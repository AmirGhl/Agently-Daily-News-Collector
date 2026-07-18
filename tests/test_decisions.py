import unittest

from news_collector.decisions import enrich_story_actions
from news_collector.html_report import render_html
from news_collector.delivery import compose_story_message


class DecisionEnrichmentTests(unittest.TestCase):
    def test_adds_a_safe_action_for_an_advisory_without_model_output(self):
        stories = enrich_story_actions(
            [
                {
                    "title": "Critical CVE affects demo-package",
                    "kind": "advisory",
                    "summary": "Upgrade to the fixed version.",
                }
            ],
            language="English",
        )

        self.assertEqual(stories[0]["action"], "ACT NOW")
        self.assertEqual(stories[0]["urgency"], "high")
        self.assertTrue(stories[0]["action_reason"])

    def test_preserves_valid_editorial_decision_and_normalizes_urgency(self):
        stories = enrich_story_actions(
            [
                {
                    "title": "A tool worth trying",
                    "action": "explore",
                    "urgency": "MEDIUM",
                    "action_reason": "Useful for a small prototype.",
                }
            ],
            language="English",
        )

        self.assertEqual(stories[0]["action"], "EXPLORE")
        self.assertEqual(stories[0]["urgency"], "medium")
        self.assertEqual(stories[0]["action_reason"], "Useful for a small prototype.")

    def test_html_report_exposes_a_morning_decision_card(self):
        html = render_html(
            report_title="Brief",
            generated_at="2026-07-19 09:00",
            topic="AI",
            language="English",
            model_label="test",
            columns=[
                {
                    "title": "Security",
                    "news_list": [
                        {
                            "title": "Patch now",
                            "url": "https://example.com",
                            "kind": "advisory",
                            "action": "ACT NOW",
                            "urgency": "high",
                            "action_reason": "A fixed version is available.",
                        }
                    ],
                }
            ],
        )

        self.assertIn("Morning brief", html)
        self.assertIn("ACT NOW", html)

    def test_telegram_story_includes_the_suggested_action(self):
        message = compose_story_message(
            {
                "title": "Patch now",
                "action": "ACT NOW",
                "action_reason": "A fixed version is available.",
            },
            column_title="Security",
            position="1/1",
            labels={"action": "Suggested action"},
            limit=4096,
        )

        self.assertIn("Suggested action:</b> ACT NOW", message)


if __name__ == "__main__":
    unittest.main()
