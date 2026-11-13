import unittest

from backend.dialogue import (
    adjust_item,
    build_bill,
    confirm_order,
    initial_state,
    process_turn,
    review_order,
)
from backend.matching import fuzzy_item, match_order
from backend.menu import LOCALIZED_MENU_NAMES, MENU


class MatchingTests(unittest.TestCase):
    def test_menu_has_twenty_items_and_matches_english_and_kannada(self):
        self.assertEqual(len(MENU), 20)
        self.assertEqual(len({item["key"] for item in MENU}), 20)
        for item in MENU:
            for phrase in (f'2 {item["romanization"]}', f'ಎರಡು {item["kannada"]}'):
                with self.subTest(item=item["key"], phrase=phrase):
                    result = match_order(phrase, {item["key"]: 2})
                    self.assertEqual(result["found"][item["key"]], 2)

    def test_multiple_items_and_word_order_are_matched(self):
        for phrase in (
            "ಎರಡು ಇಡ್ಲಿ ಮತ್ತು ಒಂದು ಕಾಫಿ",
            "ಒಂದು ಕಾಫಿ ಎರಡು ಇಡ್ಲಿ",
            "2 idlis and 1 coffee",
            "one coffee, two idly",
        ):
            with self.subTest(phrase=phrase):
                result = match_order(phrase, {"idli": 0, "coffee": 0})
                self.assertEqual(result["found"], {"idli": 2, "coffee": 1})

    def test_item_first_quantity_lists_assign_each_quantity_to_the_preceding_item_once(self):
        phrase = "bisbele bath 2, cfee 3, poori 1"
        result = match_order(
            phrase,
            {"bisi_bele_bath": 0, "coffee": 0, "puri": 0},
        )
        self.assertEqual(
            result["found"],
            {"bisi_bele_bath": 2, "coffee": 3, "puri": 1},
        )

    def test_quantity_after_conjunction_belongs_to_the_following_item(self):
        result = match_order("coffee and 3 poori", {"coffee": 0, "puri": 0})
        self.assertEqual(result["found"], {"coffee": 1, "puri": 3})

    def test_near_miss_preserves_each_item_quantity(self):
        result = match_order("ಎರಡು ಇಡ್ಲಿ", {"idli": 0, "coffee": 0})
        self.assertEqual(result["found"], {"idli": 2, "coffee": 0})

    def test_fuzzy_matching_recognizes_common_spelling_variants(self):
        self.assertEqual(fuzzy_item("idlee"), "idli")
        self.assertEqual(fuzzy_item("cofee"), "coffee")

    def test_quantity_and_kannada_case_variants_match_menu_items(self):
        cases = (
            ("ಎರಡನ್ನು ಇಡ್ಲಿ", "idli", 2),
            ("ಎರಡು ಇಡ್ಲಿಯನ್ನು", "idli", 2),
            ("ಒಂದು ಕಾಫಿಯನ್ನು", "coffee", 1),
            ("ಎರಡು ವಡೆಯನ್ನು", "vada", 2),
            ("remove 2 of the idlis", "idli", 2),
        )
        for phrase, key, quantity in cases:
            with self.subTest(phrase=phrase):
                result = match_order(phrase, {key: 0})
                self.assertEqual(result["found"][key], quantity)

    def test_tamil_and_telugu_names_and_quantities_match_the_whole_menu(self):
        language_quantities = {"ta": "இரண்டு", "te": "రెండు"}
        for language, quantity in language_quantities.items():
            for key, names in LOCALIZED_MENU_NAMES.items():
                phrase = f"{quantity} {names[language][0]}"
                with self.subTest(language=language, item=key, phrase=phrase):
                    result = match_order(phrase, {key: 0})
                    self.assertEqual(result["found"][key], 2)

    def test_tamil_and_telugu_mixed_order_phrases_match_items(self):
        cases = (
            ("இரண்டு இட்லி மற்றும் ஒரு காபி", {"idli": 2, "coffee": 1}),
            ("రెండు ఇడ్లీలు మరియు ఒక కాఫీ", {"idli": 2, "coffee": 1}),
            ("இரண்டு idli and one coffee", {"idli": 2, "coffee": 1}),
            ("రెండు idli and one coffee", {"idli": 2, "coffee": 1}),
            ("add two இட்லி", {"idli": 2}),
            ("add two ఇడ్లీలు", {"idli": 2}),
        )
        for phrase, expected in cases:
            with self.subTest(phrase=phrase):
                result = match_order(phrase, {key: 0 for key in expected})
                self.assertEqual(result["found"], expected)

    def test_tamil_and_telugu_quantity_words_zero_through_ten_and_native_digits(self):
        quantities = {
            "ta": (
                "பூஜ்ஜியம்", "ஒன்று", "இரண்டு", "மூன்று", "நான்கு", "ஐந்து",
                "ஆறு", "ஏழு", "எட்டு", "ஒன்பது", "பத்து",
            ),
            "te": (
                "సున్నా", "ఒకటి", "రెండు", "మూడు", "నాలుగు", "ఐదు",
                "ఆరు", "ఏడు", "ఎనిమిది", "తొమ్మిది", "పది",
            ),
        }
        for language, words in quantities.items():
            item_name = LOCALIZED_MENU_NAMES["idli"][language][0]
            for expected, word in enumerate(words):
                with self.subTest(language=language, quantity=word):
                    result = match_order(f"{word} {item_name}", {"idli": 0})
                    self.assertEqual(result["found"]["idli"], expected)
        self.assertEqual(match_order("௨ idli", {"idli": 0})["found"]["idli"], 2)
        self.assertEqual(match_order("౨ idli", {"idli": 0})["found"]["idli"], 2)


class OrderingTests(unittest.TestCase):
    def test_item_first_quantity_list_updates_the_intended_items(self):
        state = initial_state()
        state, result = process_turn(state, "bisbele bath 2, cfee 3, poori 1")
        self.assertEqual(
            state["order"],
            {"bisi_bele_bath": 2, "coffee": 3, "puri": 1},
        )
        self.assertTrue(result["order_updated"])

    def test_spoken_items_accumulate_in_the_basket(self):
        state = initial_state()
        state, first = process_turn(state, "ಎರಡು ಇಡ್ಲಿ")
        self.assertEqual(state["order"], {"idli": 2})
        self.assertTrue(first["order_updated"])

        state, second = process_turn(state, "one coffee and one masala dosa")
        self.assertEqual(state["order"], {"idli": 2, "coffee": 1, "masala_dosa": 1})
        self.assertEqual(second["order_added"], {"coffee": 1, "masala_dosa": 1})
        self.assertEqual(second["scene"]["order_total"], 165)

    def test_spoken_remove_changes_basket_and_subtotal(self):
        state = initial_state()
        state, _ = process_turn(state, "two idlis and one coffee")
        state, result = process_turn(state, "remove one idli")
        self.assertEqual(state["order"], {"idli": 1, "coffee": 1})
        self.assertTrue(result["order_updated"])
        self.assertEqual(result["scene"]["order_total"], 55)

    def test_voice_remove_phrases_remove_one_or_the_requested_item_count(self):
        cases = (
            ("remove one idli", {"idli": 2}),
            ("remove two idlis", {"idli": 1}),
            ("remove two of the idlis", {"idli": 1}),
            ("take off two idlis", {"idli": 1}),
            ("remove idli", {}),
            ("no idli please", {}),
            ("I don't want idli", {}),
            ("I do not need idli", {}),
            ("ಇಡ್ಲಿ ಬೇಡ", {}),
            ("ಒಂದು ಇಡ್ಲಿ ತೆಗೆದುಹಾಕಿ", {"idli": 2}),
            ("ಎರಡು ಇಡ್ಲಿಯನ್ನು ತೆಗೆದುಹಾಕಿ", {"idli": 1}),
        )
        for phrase, expected_order in cases:
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 3}
                state, result = process_turn(state, phrase)
                self.assertEqual(state["order"], expected_order)
                self.assertTrue(result["order_updated"])

    def test_voice_reduce_and_set_quantity_phrases_are_distinct(self):
        cases = (
            ("reduce idli by two", {"idli": 1}),
            ("decrease idli", {"idli": 2}),
            ("two idli ಕಡಿಮೆ ಮಾಡಿ", {"idli": 1}),
            ("reduce idli to one", {"idli": 1}),
            ("decrease idli to one", {"idli": 1}),
            ("reduce idli from three to one", {"idli": 1}),
            ("reduce 3 idli to 1 idli", {"idli": 1}),
            ("reduce idli to 1 idli", {"idli": 1}),
            ("set 3 idli to 1 idli", {"idli": 1}),
            ("increase idli by two", {"idli": 5}),
            ("make it one idli", {"idli": 1}),
            ("change idli to zero", {}),
        )
        for phrase, expected_order in cases:
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 3}
                state, _ = process_turn(state, phrase)
                self.assertEqual(state["order"], expected_order)

    def test_kannada_equivalent_wording_maps_to_safe_item_intents(self):
        cases = (
            ("ಇಡ್ಲಿ ಒಂದನ್ನು ಕಡಿಮೆ ಮಾಡಿ", {"idli": 2, "coffee": 1}),
            ("ಒಂದನ್ನು ಕಡಿಮೆ ಮಾಡಿ ಇಡ್ಲಿ", {"idli": 2, "coffee": 1}),
            ("one less idli", {"idli": 2, "coffee": 1}),
            ("ಇಡ್ಲಿ ಒಂದೇ ಇರಲಿ", {"idli": 1, "coffee": 1}),
            ("ಇಡ್ಲಿ ಒಂದು ಸಾಕು", {"idli": 1, "coffee": 1}),
            ("ಇನ್ನೊಂದು ಇಡ್ಲಿ ಸೇರಿಸಿ", {"idli": 4, "coffee": 1}),
            ("ಇಡ್ಲಿ ಕಡಿಮೆ ಮಾಡಬೇಡಿ", {"idli": 3, "coffee": 1}),
        )
        for phrase, expected_order in cases:
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 3, "coffee": 1}
                state, _ = process_turn(state, phrase)
                self.assertEqual(state["order"], expected_order)

    def test_kannada_ambiguous_edit_asks_without_changing_basket(self):
        state = initial_state()
        state["order"] = {"idli": 3, "coffee": 1}
        next_state, result = process_turn(state, "reduce it")
        self.assertEqual(next_state["order"], {"idli": 3, "coffee": 1})
        self.assertTrue(result["clarification_required"])
        self.assertIn("ಪದಾರ್ಥ", result["hint"])

    def test_set_quantity_with_repeated_item_keeps_other_basket_items(self):
        state = initial_state()
        state["order"] = {"idli": 3, "coffee": 1}
        state, result = process_turn(state, "reduce 3 idli to 1 idli")
        self.assertEqual(state["order"], {"idli": 1, "coffee": 1})
        self.assertEqual(result["order_changes"], {"idli": 1})

    def test_kannada_spoken_edits_change_only_the_requested_item(self):
        cases = (
            ("ಒಂದು ಇಡ್ಲಿಯನ್ನು ತೆಗೆದುಹಾಕಿ", {"idli": 2, "coffee": 2, "vada": 1}),
            ("ಎರಡು ಇಡ್ಲಿಯನ್ನು ತೆಗೆದುಹಾಕಿ", {"idli": 1, "coffee": 2, "vada": 1}),
            ("ಇಡ್ಲಿ ಎರಡು ಕಡಿಮೆ ಮಾಡಿ", {"idli": 1, "coffee": 2, "vada": 1}),
            ("ಇಡ್ಲಿ ಬೇಡ", {"coffee": 2, "vada": 1}),
            ("ಇನ್ನೂ ಎರಡು ಇಡ್ಲಿ ಸೇರಿಸಿ", {"idli": 5, "coffee": 2, "vada": 1}),
            ("ಇಡ್ಲಿ ಒಂದನ್ನು ಹೆಚ್ಚಿಸಿ", {"idli": 4, "coffee": 2, "vada": 1}),
            ("ಇನ್ನೊಂದು ಇಡ್ಲಿ ಸೇರಿಸಿ", {"idli": 4, "coffee": 2, "vada": 1}),
            ("ಮೂರು ಇಡ್ಲಿ ಒಂದು ಇಡ್ಲಿಗೆ ಕಡಿಮೆ ಮಾಡಿ", {"idli": 1, "coffee": 2, "vada": 1}),
            ("ಇಡ್ಲಿಯನ್ನು ಮೂರರಿಂದ ಒಂದಕ್ಕೆ ಇಳಿಸಿ", {"idli": 1, "coffee": 2, "vada": 1}),
        )
        for phrase, expected_order in cases:
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 3, "coffee": 2, "vada": 1}
                state, result = process_turn(state, phrase)
                self.assertEqual(state["order"], expected_order)
                self.assertTrue(result["order_updated"])

    def test_tamil_and_telugu_edits_preserve_unmentioned_items(self):
        cases = (
            ("ஒரு இட்லியை நீக்குங்கள்", {"idli": 2, "coffee": 1}),
            ("இட்லி ஒன்றை குறைக்கவும்", {"idli": 2, "coffee": 1}),
            ("ஐந்து இட்லி ஒன்றாக மாற்றுங்கள்", {"idli": 1, "coffee": 1}),
            ("ఒక ఇడ్లీ తీసేయండి", {"idli": 2, "coffee": 1}),
            ("ఇడ్లీ ఒకటి తగ్గించండి", {"idli": 2, "coffee": 1}),
            ("ఐదు ఇడ్లీ ఒకటికి తగ్గించండి", {"idli": 1, "coffee": 1}),
            ("இன்னும் இரண்டு இட்லி சேர்க்கவும்", {"idli": 5, "coffee": 1}),
            ("ఇంకా రెండు ఇడ్లీలు వేయండి", {"idli": 5, "coffee": 1}),
        )
        for phrase, expected_order in cases:
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 3, "coffee": 1}
                state, result = process_turn(state, phrase)
                self.assertEqual(state["order"], expected_order)
                self.assertTrue(result["order_updated"])

    def test_tamil_and_telugu_corrections_and_whole_order_cancellation(self):
        cases = (
            ("மூன்று இட்லி உண்மையில் இரண்டு இட்லி", {"idli": 2, "coffee": 1}),
            ("మూడు ఇడ్లీ నిజానికి రెండు ఇడ్లీ", {"idli": 2, "coffee": 1}),
        )
        for phrase, expected_order in cases:
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 3, "coffee": 1}
                state, _ = process_turn(state, phrase)
                self.assertEqual(state["order"], expected_order)

        for language, phrase in (
            ("ta", "என் ஆர்டரை ரத்து செய்யுங்கள்"),
            ("te", "నా ఆర్డర్ రద్దు చేయండి"),
        ):
            with self.subTest(language=language):
                state = initial_state(language=language)
                state["order"] = {"idli": 2, "coffee": 1}
                state, result = process_turn(state, phrase)
                self.assertEqual(state["order"], {})
                self.assertEqual(result["line"], {
                    "ta": "கூடை காலியாக உள்ளது. வேண்டிய பொருளையும் எண்ணிக்கையையும் சொல்லுங்கள் அல்லது மெனுவிலிருந்து தேர்வு செய்யுங்கள்.",
                    "te": "బుట్ట ఖాళీగా ఉంది. పదార్థం, సంఖ్య చెప్పండి లేదా మెనూ నుంచి ఎంచుకోండి.",
                }[language])

    def test_tamil_and_telugu_cancel_item_clarify_and_reject_mixed_overflow(self):
        cases = (
            ("ta", "ஒரு காபி வேண்டாம்", "ஒன்றை நீக்குங்கள்", "பத்து இட்லி மற்றும் ஒரு காபி சேர்க்கவும்"),
            ("te", "ఒక కాఫీ వద్దు", "ఒకటి తీసేయండి", "పది ఇడ్లీలు మరియు ఒక కాఫీ వేయండి"),
        )
        for language, remove_item, vague_edit, overflow in cases:
            with self.subTest(language=language):
                state = initial_state(language=language)
                state["order"] = {"idli": 3, "coffee": 1}
                state, removed = process_turn(state, remove_item)
                self.assertEqual(state["order"], {"idli": 3})
                self.assertTrue(removed["order_updated"])

                state, ambiguous = process_turn(state, vague_edit)
                self.assertEqual(state["order"], {"idli": 3})
                self.assertTrue(ambiguous["clarification_required"])

                state["order"] = {"idli": 2, "coffee": 1}
                state, limited = process_turn(state, overflow)
                self.assertEqual(state["order"], {"idli": 2, "coffee": 1})
                self.assertTrue(limited["quantity_limit_exceeded"])
                self.assertFalse(limited["order_updated"])

    def test_tamil_and_telugu_set_quantity_to_zero_and_negative_confirmation(self):
        for language, set_zero, review, negated_confirm in (
            ("ta", "இட்லியை பூஜ்ஜியமாக மாற்றுங்கள்", "அவ்வளவுதான்", "உறுதிப்படுத்த வேண்டாம்"),
            ("te", "ఇడ్లీని సున్నాగా మార్చండి", "ఇంతే", "ఖరారు చేయవద్దు"),
        ):
            with self.subTest(language=language):
                state = initial_state(language=language)
                state["order"] = {"idli": 3, "coffee": 1}
                state, result = process_turn(state, set_zero)
                self.assertEqual(state["order"], {"coffee": 1})
                self.assertTrue(result["order_updated"])
                state, review_result = process_turn(state, review)
                self.assertTrue(state["reviewing"])
                self.assertTrue(review_result["order_review"])
                state, negative = process_turn(state, negated_confirm)
                self.assertFalse(state["complete"])
                self.assertTrue(state["reviewing"])
                self.assertEqual(state["order"], {"coffee": 1})
                self.assertFalse(negative.get("order_confirmed", False))

    def test_tamil_and_telugu_review_confirmation_and_localized_receipt(self):
        cases = (
            ("ta", "இரண்டு இட்லி", "அவ்வளவுதான்", "உறுதிப்படுத்துங்கள்", "இட்லி"),
            ("te", "రెండు ఇడ్లీలు", "ఇంతే", "ఖరారు చేయండి", "ఇడ్లీ"),
        )
        for language, order, review, confirm, item_title in cases:
            with self.subTest(language=language):
                state = initial_state(language=language)
                state, _ = process_turn(state, order)
                state, review_result = process_turn(state, review)
                self.assertTrue(state["reviewing"])
                self.assertEqual(review_result["line"], {
                    "ta": "இது உங்கள் ஆர்டர். சரியாக இருந்தால் “உறுதிப்படுத்துங்கள்” என்று சொல்லுங்கள்; மாற்றம் வேண்டுமெனில் என்ன மாற்ற வேண்டும் என்று சொல்லுங்கள்.",
                    "te": "ఇది మీ ఆర్డర్. సరిగ్గా ఉంటే “ఖరారు చేయండి” అని చెప్పండి; మార్చాలంటే ఏమి మార్చాలో చెప్పండి.",
                }[language])
                state, receipt = process_turn(state, confirm)
                self.assertTrue(state["complete"])
                self.assertEqual(receipt["bill"]["items"][0]["title"], item_title)

    def test_mixed_voice_commands_apply_to_their_own_items(self):
        state = initial_state()
        state["order"] = {"idli": 2, "coffee": 1}
        state, result = process_turn(state, "remove one idli and add two coffee")
        self.assertEqual(state["order"], {"idli": 1, "coffee": 3})
        self.assertEqual(result["line_key"], "order_changed")

        state, _ = process_turn(state, "not idli but add one vada")
        self.assertEqual(state["order"], {"coffee": 3, "vada": 1})

        state, _ = process_turn(state, "remove coffee and vada")
        self.assertEqual(state["order"], {})

    def test_voice_changes_can_remove_then_readd_the_same_item_in_one_turn(self):
        state = initial_state()
        state["order"] = {"idli": 3}
        state, result = process_turn(state, "remove two idli and add one idli")
        self.assertEqual(state["order"], {"idli": 2})
        self.assertEqual(result["line_key"], "order_changed")

    def test_explicit_correction_replaces_a_false_start_instead_of_adding_both(self):
        cases = (
            ("three idli, actually make that two", {"idli": 2}),
            ("three idli, I mean two idli", {"idli": 2}),
            ("three idli, scratch that, add two idli", {"idli": 2}),
        )
        for phrase, expected_order in cases:
            with self.subTest(phrase=phrase):
                state = initial_state()
                state, _ = process_turn(state, phrase)
                self.assertEqual(state["order"], expected_order)

    def test_ambiguous_corrections_never_guess_which_item_to_change(self):
        state = initial_state()
        state["order"] = {"idli": 3, "coffee": 1}
        state, result = process_turn(state, "three idli and one coffee, actually make that two")
        self.assertEqual(state["order"], {"idli": 3, "coffee": 1})
        self.assertTrue(result["clarification_required"])

    def test_add_and_set_quantity_phrases_are_distinct(self):
        state = initial_state()
        state["order"] = {"idli": 3}
        state, _ = process_turn(state, "add one more idli")
        self.assertEqual(state["order"], {"idli": 4})

        state, _ = process_turn(state, "make it one idli")
        self.assertEqual(state["order"], {"idli": 1})

    def test_vague_item_references_ask_instead_of_changing_the_basket(self):
        for phrase in ("remove one", "make it two", "remove the last item", "cancel it"):
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 2, "coffee": 1}
                state, result = process_turn(state, phrase)
                self.assertEqual(state["order"], {"idli": 2, "coffee": 1})
                self.assertTrue(result["clarification_required"])
                self.assertFalse(result["order_updated"])

    def test_mixed_keep_and_negated_actions_only_change_requested_items(self):
        cases = (
            ("remove one idli and keep coffee", {"idli": 1, "coffee": 2, "vada": 1}),
            ("remove one idli and do not remove coffee", {"idli": 1, "coffee": 2, "vada": 1}),
            ("remove one idli, don't change coffee, add one vada", {"idli": 1, "coffee": 2, "vada": 2}),
        )
        for phrase, expected_order in cases:
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 2, "coffee": 2, "vada": 1}
                state, _ = process_turn(state, phrase)
                self.assertEqual(state["order"], expected_order)

    def test_canceling_a_named_item_or_negating_a_cancel_never_clears_the_basket(self):
        state = initial_state()
        state["order"] = {"idli": 2, "coffee": 1}
        state, result = process_turn(state, "cancel idli")
        self.assertEqual(state["order"], {"coffee": 1})
        self.assertTrue(result["order_updated"])

        state["order"] = {"idli": 2, "coffee": 1}
        state, result = process_turn(state, "don't cancel my order")
        self.assertEqual(state["order"], {"idli": 2, "coffee": 1})
        self.assertFalse(result["order_updated"])

    def test_unclear_and_partial_transcripts_leave_the_basket_unchanged(self):
        for phrase in ("", "two", "please", "add", "remove two please"):
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 2, "coffee": 1}
                state, result = process_turn(state, phrase)
                self.assertEqual(state["order"], {"idli": 2, "coffee": 1})
                self.assertFalse(result["order_updated"])

    def test_spoken_quantity_boundaries_are_explicit_and_never_partially_applied(self):
        state = initial_state()
        state["order"] = {"idli": 10, "coffee": 1}
        unchanged, result = process_turn(state, "add one vada and one idli")
        self.assertEqual(unchanged["order"], {"idli": 10, "coffee": 1})
        self.assertEqual(result["line_key"], "quantity_limit")
        self.assertTrue(result["quantity_limit_exceeded"])
        self.assertFalse(result["order_updated"])
        self.assertEqual(state["order"], {"idli": 10, "coffee": 1})

        state, result = process_turn(state, "remove five idli")
        self.assertEqual(state["order"], {"idli": 5, "coffee": 1})
        self.assertTrue(result["order_updated"])

        state, result = process_turn(state, "set idli to zero")
        self.assertEqual(state["order"], {"coffee": 1})
        self.assertTrue(result["order_updated"])

    def test_kannada_quantity_limit_hint_is_localized(self):
        state = initial_state()
        state["order"] = {"idli": 10}
        unchanged, result = process_turn(state, "ಇನ್ನೊಂದು ಇಡ್ಲಿ ಸೇರಿಸಿ")
        self.assertEqual(unchanged["order"], {"idli": 10})
        self.assertTrue(result["quantity_limit_exceeded"])
        self.assertIn("ಗರಿಷ್ಠ ಹತ್ತು", result["hint"])

    def test_code_switched_voice_edits_are_supported(self):
        state = initial_state()
        state["order"] = {"idli": 3, "coffee": 1}
        for phrase, expected_order in (
            ("ಎರಡು idli remove ಮಾಡಿ", {"idli": 1, "coffee": 1}),
            ("add ಇನ್ನೊಂದು coffee", {"idli": 1, "coffee": 2}),
            ("one coffee ಸೇರಿಸಿ", {"idli": 1, "coffee": 3}),
        ):
            with self.subTest(phrase=phrase):
                state, result = process_turn(state, phrase)
                self.assertEqual(state["order"], expected_order)
                self.assertTrue(result["order_updated"])

    def test_negated_or_ambiguous_voice_commands_never_add_items(self):
        for phrase in ("do not remove idli", "no more idli", "change idli"):
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 2}
                state, result = process_turn(state, phrase)
                self.assertEqual(state["order"], {"idli": 2})
                self.assertFalse(result["order_updated"])

    def test_voice_clear_order_phrases_empty_the_whole_basket(self):
        for phrase in (
            "clear my order",
            "remove everything",
            "remove all",
            "cancel my order",
            "cancel current order",
            "cancel this order",
            "cancel all my items",
            "remove all items",
            "clear my basket",
            "ನನ್ನ ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ",
            "ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ",
            "ಎಲ್ಲಾ ತೆಗೆದುಹಾಕಿ",
        ):
            with self.subTest(phrase=phrase):
                state = initial_state()
                state["order"] = {"idli": 2, "coffee": 1}
                state, result = process_turn(state, phrase)
                self.assertEqual(state["order"], {})
                self.assertTrue(result["order_updated"])

    def test_clear_order_then_add_item_starts_with_an_empty_basket(self):
        state = initial_state()
        state["order"] = {"idli": 2, "coffee": 1}
        state, result = process_turn(state, "clear my order and add one coffee")
        self.assertEqual(state["order"], {"coffee": 1})
        self.assertEqual(result["order_added"], {"coffee": 1})

    def test_remove_all_of_an_item_does_not_clear_other_items(self):
        state = initial_state()
        state["order"] = {"idli": 2, "coffee": 1}
        state, result = process_turn(state, "remove all idli")
        self.assertEqual(state["order"], {"coffee": 1})
        self.assertTrue(result["order_updated"])

    def test_spoken_quantity_changes_use_the_amount_after_to(self):
        state = initial_state()
        state, _ = process_turn(state, "one idli and two coffee")
        state, result = process_turn(state, "change idli to 2")
        self.assertEqual(state["order"], {"idli": 2, "coffee": 2})
        self.assertEqual(result["line_key"], "order_changed")

        state, _ = process_turn(state, "set coffee to three")
        self.assertEqual(state["order"], {"idli": 2, "coffee": 3})

    def test_direct_item_controls_add_remove_and_reject_bad_changes(self):
        state = initial_state()
        state, _ = adjust_item(state, "coffee", 2)
        self.assertEqual(state["order"], {"coffee": 2})
        state, _ = adjust_item(state, "coffee", -1)
        self.assertEqual(state["order"], {"coffee": 1})
        with self.assertRaisesRegex(ValueError, "negative"):
            adjust_item(state, "coffee", -2)
        with self.assertRaisesRegex(ValueError, "no longer available"):
            adjust_item(state, "not-a-menu-item", 1)

    def test_item_quantity_is_capped_at_ten(self):
        state = initial_state()
        state, _ = process_turn(state, "ten idli")
        state, result = process_turn(state, "one idli")
        self.assertEqual(state["order"], {"idli": 10})
        self.assertEqual(result["line_key"], "quantity_limit")
        self.assertTrue(result["quantity_limit_exceeded"])
        with self.assertRaisesRegex(ValueError, "up to 10"):
            adjust_item(state, "idli", 1)

    def test_that_is_all_can_include_the_last_items_and_starts_review(self):
        state = initial_state()
        state, result = process_turn(state, "two idlis and one coffee, that's all")
        self.assertTrue(result["order_review"])
        self.assertTrue(state["reviewing"])
        self.assertFalse(state["complete"])
        self.assertEqual(state["order"], {"idli": 2, "coffee": 1})
        self.assertEqual(result["scene"]["stage_key"], "review")

    def test_review_requires_items_and_does_not_confirm_the_order(self):
        state = initial_state()
        state, empty = review_order(state)
        self.assertEqual(empty["line_key"], "empty_order")
        self.assertFalse(state["reviewing"])
        with self.assertRaisesRegex(ValueError, "Review your basket"):
            confirm_order(state)

        state, _ = process_turn(state, "one tea")
        state, review = review_order(state)
        self.assertTrue(review["order_review"])
        self.assertTrue(state["reviewing"])
        self.assertFalse(state["complete"])

    def test_review_can_be_cancelled_and_order_edited(self):
        state = initial_state()
        state, _ = process_turn(state, "one coffee")
        state, _ = review_order(state)
        state, cancelled = process_turn(state, "keep shopping")
        self.assertFalse(state["reviewing"])
        self.assertEqual(cancelled["line_key"], "order_cancelled")

        state, _ = process_turn(state, "add two idlis")
        self.assertEqual(state["order"], {"coffee": 1, "idli": 2})

    def test_review_basket_can_be_modified_and_explicitly_confirmed(self):
        state = initial_state()
        state, _ = process_turn(state, "two idlis and one coffee")
        state, _ = review_order(state)
        state, _ = adjust_item(state, "idli", -1)
        self.assertTrue(state["reviewing"])
        self.assertEqual(state["order"], {"idli": 1, "coffee": 1})

        state, confirmed = process_turn(state, "confirm order")
        self.assertTrue(state["complete"])
        self.assertFalse(state["reviewing"])
        self.assertEqual(confirmed["line_key"], "order_confirmed")
        self.assertEqual(confirmed["bill"]["total"], 55)

    def test_negated_confirmation_does_not_place_the_order(self):
        state = initial_state()
        state, _ = process_turn(state, "one tea")
        state, _ = review_order(state)
        for phrase in ("do not confirm order", "I don't want to confirm order"):
            with self.subTest(phrase=phrase):
                state, result = process_turn(state, phrase)
                self.assertTrue(state["reviewing"])
                self.assertFalse(state["complete"])
                self.assertTrue(result["clarification_required"])

    def test_confirmation_produces_an_itemized_inr_receipt(self):
        state = initial_state()
        state, _ = process_turn(state, "two masala dosa, one tea, one water")
        state, _ = review_order(state)
        state, result = confirm_order(state)

        self.assertTrue(state["complete"])
        self.assertEqual(result["bill"], {
            "items": [
                {"key": "masala_dosa", "title": "ಮಸಾಲೆ ದೋಸೆ", "quantity": 2, "unit_price": 80, "line_total": 160},
                {"key": "tea", "title": "ಚಹಾ", "quantity": 1, "unit_price": 15, "line_total": 15},
                {"key": "water", "title": "ನೀರು", "quantity": 1, "unit_price": 20, "line_total": 20},
            ],
            "subtotal": 195,
            "total": 195,
            "currency": "INR",
        })
        self.assertEqual(build_bill(state["order"])["total"], 195)

    def test_unrecognized_phrase_does_not_change_the_basket(self):
        state = initial_state()
        state, _ = process_turn(state, "two idlis")
        state, result = process_turn(state, "hello there")
        self.assertFalse(result["matched"])
        self.assertEqual(state["order"], {"idli": 2})

    def test_confirmed_order_cannot_be_changed_or_confirmed_again(self):
        state = initial_state()
        state, _ = process_turn(state, "one idli")
        state, _ = review_order(state)
        state, _ = confirm_order(state)
        with self.assertRaisesRegex(ValueError, "already confirmed"):
            process_turn(state, "one coffee")
        with self.assertRaisesRegex(ValueError, "already been confirmed"):
            review_order(state)


if __name__ == "__main__":
    unittest.main()
