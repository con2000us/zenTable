from manim import *

# Render example:
# manim -pqh doc/interaction/manim_storyboard.py ThreeCaseStoryboard


class ThreeCaseStoryboard(Scene):
    def title_card(self):
        title = Text("ZenTable Beta Demo", font_size=56, weight=BOLD)
        subtitle = Text("Problem-Solving Storyboard", font_size=30, color=BLUE_B)
        subtitle.next_to(title, DOWN, buff=0.3)

        self.play(FadeIn(title, shift=UP * 0.2), FadeIn(subtitle, shift=UP * 0.2))
        self.wait(1.2)
        self.play(FadeOut(title), FadeOut(subtitle))

    def case_block(self, idx, case_title, problem, actions, result):
        badge = RoundedRectangle(corner_radius=0.15, width=1.8, height=0.6, fill_opacity=1, fill_color=BLUE_E, stroke_width=0)
        badge_txt = Text(f"Case {idx}", font_size=26, color=WHITE, weight=BOLD).move_to(badge)
        case = VGroup(badge, badge_txt).to_edge(UL).shift(DOWN * 0.2 + RIGHT * 0.2)

        title = Text(case_title, font_size=40, weight=BOLD).next_to(case, RIGHT, buff=0.5).align_to(case, UP)

        problem_box = RoundedRectangle(corner_radius=0.2, width=12.2, height=1.4, color=RED_B)
        problem_label = Text("Problem", font_size=24, color=RED_B, weight=BOLD).next_to(problem_box, LEFT, buff=0.25)
        problem_text = Text(problem, font_size=26).move_to(problem_box)
        problem_group = VGroup(problem_box, problem_label, problem_text).move_to(UP * 1.8)

        action_box = RoundedRectangle(corner_radius=0.2, width=12.2, height=2.2, color=YELLOW_B)
        action_label = Text("Action", font_size=24, color=YELLOW_D, weight=BOLD).next_to(action_box, LEFT, buff=0.25)
        action_lines = VGroup(*[Text(f"• {a}", font_size=24) for a in actions]).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        action_lines.move_to(action_box)
        action_group = VGroup(action_box, action_label, action_lines).move_to(ORIGIN)

        result_box = RoundedRectangle(corner_radius=0.2, width=12.2, height=1.5, color=GREEN_B)
        result_label = Text("Result", font_size=24, color=GREEN_D, weight=BOLD).next_to(result_box, LEFT, buff=0.25)
        result_text = Text(result, font_size=26, color=GREEN_A).move_to(result_box)
        result_group = VGroup(result_box, result_label, result_text).move_to(DOWN * 2)

        self.play(FadeIn(case), FadeIn(title, shift=RIGHT * 0.2))
        self.play(Create(problem_box), FadeIn(problem_label), Write(problem_text))
        self.wait(0.4)
        self.play(Create(action_box), FadeIn(action_label), LaggedStart(*[Write(x) for x in action_lines], lag_ratio=0.2))
        self.wait(0.6)
        self.play(Create(result_box), FadeIn(result_label), Write(result_text))
        self.wait(1.4)

        self.play(*[FadeOut(m) for m in [case, title, problem_group, action_group, result_group]])

    def construct(self):
        self.camera.background_color = "#0B1020"

        self.title_card()

        self.case_block(
            1,
            "A4 Photo → Clean Table Output",
            "Phone-captured A4 table is skewed, noisy, and hard to read",
            [
                "OCR extract + normalize rows",
                "Sort by score descending",
                "Apply threshold highlights (success / warning / danger)",
                "Render with CSS theme",
            ],
            "Readable, share-ready table image generated from raw photo input",
        )

        self.case_block(
            2,
            "Broken ASCII → Structured CSS",
            "Plain-text table collapses spacing in chat and loses alignment",
            [
                "Parse and normalize malformed text",
                "Apply semantic smart-wrap",
                "Render with minimal_ios_mobile theme",
            ],
            "From broken monospace layout to stable visual table output",
        )

        self.case_block(
            3,
            "Fragmented Crops → Merged Decision View",
            "Multiple cropped table fragments split context and hide trends",
            [
                "Merge fragmented table parts",
                "Filter key columns only",
                "Highlight outliers and export final view",
            ],
            "One coherent decision-ready table from fragmented sources",
        )

        end = Text("ZenTable Beta · Real outputs from curated hard samples", font_size=34, color=BLUE_B)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(1.8)
        self.play(FadeOut(end))
