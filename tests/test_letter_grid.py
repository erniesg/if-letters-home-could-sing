import unittest


PHOTO_TEXT = (
    "家中寄来的话都收到了，隔着海与城，读来像灯下有人轻声叮嘱。"
    "你们汇来的钱已到账，我先缴了本学期学费，余下留作房租和药费，账目记得清楚，请别再省自己的饭菜。"
    "父亲的咳嗽要按时复诊，母亲也莫总说不累；我每天走路，睡得尚安，功课虽紧，成绩没有落下。"
    "等课程结束，我便带着书和给家里的小礼物回去。"
    "到时换我料理窗前的花、陪你们看诊，也把这些年欠下的团圆，一顿顿补回来。"
)


class LetterGridTests(unittest.TestCase):
    def test_photographed_176_character_letter_places_every_glyph_once(self):
        from mac_bridge.letter_grid import FERRARI_GRID, place_vertical

        placements = place_vertical(PHOTO_TEXT, FERRARI_GRID)

        self.assertEqual(len(PHOTO_TEXT), 176)
        self.assertEqual(len(placements), 176)
        self.assertEqual("".join(item.glyph for item in placements), PHOTO_TEXT)
        self.assertTrue(
            all(
                0 <= item.x < FERRARI_GRID.width
                and 0 <= item.y < FERRARI_GRID.height
                for item in placements
            )
        )
        self.assertEqual(placements[-7].glyph, "一")
        self.assertEqual(placements[-1].glyph, "。")

    def test_stream_publishes_only_complete_sentences_that_fit(self):
        from mac_bridge.letter_grid import FERRARI_GRID, SentenceStream

        stream = SentenceStream(FERRARI_GRID, minimum=12)

        self.assertEqual(stream.append("家中安好，勿"), "")
        self.assertEqual(stream.append("念。功课顺利"), "家中安好，勿念。")
        self.assertEqual(stream.append("。"), "家中安好，勿念。功课顺利。")
        self.assertEqual(stream.finalize(), "家中安好，勿念。功课顺利。")

    def test_closing_punctuation_never_starts_a_visible_column(self):
        from mac_bridge.letter_grid import FERRARI_GRID, place_vertical

        placements = place_vertical("家" * 18 + "。", FERRARI_GRID)

        self.assertEqual((placements[-2].column, placements[-2].row), (1, 0))
        self.assertEqual((placements[-1].column, placements[-1].row), (1, 1))
        self.assertFalse(
            any(item.punctuation and item.row == 0 for item in placements)
        )

    def test_earlier_published_glyph_positions_never_reflow(self):
        from mac_bridge.letter_grid import FERRARI_GRID, SentenceStream, place_vertical

        stream = SentenceStream(FERRARI_GRID, minimum=1)
        first = stream.append("家中安好，勿念。")
        first_positions = place_vertical(first)
        second = stream.append("功课顺利，盼归。")

        self.assertEqual(second[: len(first)], first)
        self.assertEqual(place_vertical(second)[: len(first)], first_positions)

    def test_grid_counts_reserved_cells_against_capacity(self):
        from mac_bridge.letter_grid import FERRARI_GRID, place_vertical

        with self.assertRaisesRegex(ValueError, "letter_grid_overflow"):
            place_vertical("家" * 18 + "。" + "人" * 161, FERRARI_GRID)

    def test_finalize_rejects_incomplete_or_too_short_output(self):
        from mac_bridge.letter_grid import FERRARI_GRID, SentenceStream

        stream = SentenceStream(FERRARI_GRID, minimum=12)
        stream.append("家中安好。尚有未完")

        with self.assertRaisesRegex(ValueError, "letter_grid_underflow"):
            stream.finalize()

    def test_notebook_letter_contract_and_prompt_match_the_grid(self):
        from mac_bridge.codex_app_server import incoming_letter_prompt
        from mac_bridge.contracts import (
            MAX_LETTER,
            MIN_NOTEBOOK_LETTER,
            ReviewContractError,
            parse_letter_text,
        )

        self.assertEqual(MAX_LETTER, 180)
        self.assertEqual(MIN_NOTEBOOK_LETTER, 144)
        self.assertIn("150 to 168 Chinese characters", incoming_letter_prompt("care"))
        self.assertIn("never exceed 180 including punctuation", incoming_letter_prompt("care"))
        self.assertEqual(
            parse_letter_text("家" * 144, minimum=MIN_NOTEBOOK_LETTER).body,
            "家" * 144,
        )
        with self.assertRaisesRegex(ReviewContractError, "too short"):
            parse_letter_text("家" * 143, minimum=MIN_NOTEBOOK_LETTER)
        with self.assertRaisesRegex(ReviewContractError, "too long"):
            parse_letter_text("家" * 181)


if __name__ == "__main__":
    unittest.main()
