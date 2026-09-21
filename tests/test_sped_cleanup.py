import unittest

from services.sped_cleanup import (
    analyze_0200_duplicates,
    count_records,
    recalculate_sped_totals,
    remove_0200_duplicates,
    remove_c101_records,
)


def field(line, position):
    return line.split("|")[position]


def find_record(lines, record_code):
    return next(line for line in lines if field(line, 1) == record_code)


def find_9900(lines, target):
    return next(
        line
        for line in lines
        if field(line, 1) == "9900" and field(line, 2) == target
    )


class SpedCleanupTests(unittest.TestCase):
    def setUp(self):
        self.corpo = [
            "|0000|020|0|01082026|31082026|EMPRESA|00000000000000|||||||||",
            "|0200|ITEM1|Produto||||UN|00||||18||",
            "|0200|ITEM1|Produto completo|789|ANT|UN|00|12345678|||18|1234567|",
            "|0220|FD|5||",
            "|0990|0|",
            "|C001|0|",
            "|C100|0|0|PART|55|00|1|1||||||||||||||||||||||||||",
            "|C101|100,00|18,00|0|0|",
            "|C990|0|",
        ]
        self.assinatura = [
            "|9001|0|",
            "|9900|0000|0|",
            "|9900|0200|0|",
            "|9900|0220|0|",
            "|9900|0990|0|",
            "|9900|C001|0|",
            "|9900|C100|0|",
            "|9900|C101|0|",
            "|9900|C990|0|",
            "|9900|9001|0|",
            "|9900|9900|0|",
            "|9900|9990|0|",
            "|9900|9999|0|",
            "|9990|0|",
            "|9999|0|",
        ]
        self.corpo, self.assinatura = recalculate_sped_totals(
            self.corpo, self.assinatura
        )

    def test_analysis_keeps_the_occurrence_with_children(self):
        analysis = analyze_0200_duplicates(self.corpo)

        self.assertEqual(analysis.duplicate_count, 1)
        self.assertEqual(analysis.removable_count, 1)
        self.assertEqual(len(analysis.groups), 1)
        self.assertEqual(analysis.groups[0].kept_index, 2)
        self.assertIn("DESCR_ITEM", analysis.groups[0].conflicting_fields)

    def test_analysis_keeps_most_complete_when_no_occurrence_has_children(self):
        analysis = analyze_0200_duplicates(
            [
                "|0200|ITEM1|Produto||||UN|00||||18||",
                "|0200|ITEM1|Produto completo|789|ANT|UN|00|12345678|||18|1234567|",
            ]
        )

        self.assertEqual(analysis.groups[0].kept_index, 1)
        self.assertEqual(analysis.removable_count, 1)

    def test_block_zero_count_includes_0000_and_0001(self):
        body, _ = recalculate_sped_totals(
            [
                "|0000|020|0|01082026|31082026|EMPRESA|00000000000000|||||||||",
                "|0001|0|",
                "|0200|ITEM1|Produto|||UN|00||||||",
                "|0990|0|",
            ],
            [],
        )

        self.assertEqual(field(find_record(body, "0990"), 2), "4")

    def test_duplicate_removal_preserves_other_records_and_updates_totals(self):
        original_children = [
            line for line in self.corpo if field(line, 1) == "0220"
        ]
        result = remove_0200_duplicates(self.corpo, self.assinatura)
        all_lines = result.corpo_sped + result.assinatura

        self.assertEqual(result.removed_count, 1)
        self.assertEqual(count_records(result.corpo_sped, "0200"), 1)
        self.assertEqual(count_records(result.corpo_sped, "0220"), 1)
        self.assertIn("Produto completo", find_record(result.corpo_sped, "0200"))
        resulting_children = [
            line for line in result.corpo_sped if field(line, 1) == "0220"
        ]
        self.assertEqual(resulting_children, original_children)
        self.assertEqual(field(find_record(result.corpo_sped, "0990"), 2), "4")
        self.assertEqual(field(find_9900(result.assinatura, "0200"), 3), "1")
        self.assertEqual(
            field(find_record(result.assinatura, "9990"), 2),
            str(len(result.assinatura)),
        )
        self.assertEqual(field(find_record(result.assinatura, "9999"), 2), str(len(all_lines)))

    def test_child_bearing_occurrence_wins_over_more_complete_occurrence(self):
        body = [
            "|0000|020|0|01082026|31082026|EMPRESA|00000000000000|||||||||",
            "|0200|ITEM1|Produto||||UN|00||||18||",
            "|0220|CX|10||",
            "|0200|OUTRO|Outro produto|||UN|00||||||",
            "|0200|ITEM1|Produto completo|789|ANT|UN|00|12345678|||18|1234567|",
            "|0990|0|",
        ]

        result = remove_0200_duplicates(body, [])

        self.assertEqual(result.removed_count, 1)
        self.assertIn(body[1], result.corpo_sped)
        self.assertNotIn(body[4], result.corpo_sped)
        self.assertEqual(
            [line for line in result.corpo_sped if field(line, 1) == "0220"],
            [body[2]],
        )

    def test_group_with_children_in_multiple_occurrences_is_not_removed(self):
        body, signature = recalculate_sped_totals(
            [
                "|0000|020|0|01082026|31082026|EMPRESA|00000000000000|||||||||",
                "|0200|ITEM1|Produto||||UN|00||||18||",
                "|0220|CX|10||",
                "|0200|ITEM1|Produto completo|789|ANT|UN|00|12345678|||18|1234567|",
                "|0220|FD|5||",
                "|0990|0|",
            ],
            [],
        )

        analysis = analyze_0200_duplicates(body)
        result = remove_0200_duplicates(body, signature)

        self.assertEqual(analysis.duplicate_count, 1)
        self.assertEqual(analysis.removable_count, 0)
        self.assertEqual(analysis.protected_group_count, 1)
        self.assertEqual(result.removed_count, 0)
        self.assertEqual(result.corpo_sped, body)

    def test_c101_removal_preserves_c100_and_updates_all_closings(self):
        result = remove_c101_records(self.corpo, self.assinatura)
        all_lines = result.corpo_sped + result.assinatura

        self.assertEqual(result.removed_count, 1)
        self.assertEqual(count_records(result.corpo_sped, "C100"), 1)
        self.assertEqual(count_records(result.corpo_sped, "C101"), 0)
        self.assertEqual(field(find_record(result.corpo_sped, "C990"), 2), "3")
        self.assertFalse(
            any(
                field(line, 1) == "9900" and field(line, 2) == "C101"
                for line in result.assinatura
            )
        )
        self.assertEqual(
            field(find_9900(result.assinatura, "9900"), 3),
            str(count_records(result.assinatura, "9900")),
        )
        self.assertEqual(field(find_record(result.assinatura, "9990"), 2), "14")
        self.assertEqual(field(find_record(result.assinatura, "9999"), 2), str(len(all_lines)))

    def test_second_duplicate_cleanup_is_idempotent(self):
        first = remove_0200_duplicates(self.corpo, self.assinatura)
        second = remove_0200_duplicates(first.corpo_sped, first.assinatura)

        self.assertEqual(second.removed_count, 0)
        self.assertEqual(second.corpo_sped, first.corpo_sped)
        self.assertEqual(second.assinatura, first.assinatura)


if __name__ == "__main__":
    unittest.main()
