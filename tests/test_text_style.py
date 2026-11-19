import unittest

from test_builder import builder, sample, render, VisibleText


class TextStyleTests(unittest.TestCase):
    def test_emphasis_highlight_and_code_preserve_escaped_content(self):
        data = sample()
        data['verdict']['summary'] = '确认**<img src=x onerror=alert(1)>**，保留==未验收==；代码 `a < b && **literal**`。'
        output = render(data)
        self.assertIn('<strong class="text-emphasis">&lt;img', output)
        self.assertIn('<mark class="text-highlight">未验收</mark>', output)
        self.assertIn('<code class="inline-code">a &lt; b &amp;&amp; **literal**</code>', output)
        self.assertNotIn('<img src=x', output)

    def test_code_stays_literal_while_emphasized_terms_remain_traceable(self):
        data = sample()
        data['glossary'] = [{'term':'SDK','explanation':'示例组件。'}]
        renderer = builder.Renderer(data)
        code = renderer.text('`SDK **literal**`')
        self.assertNotIn('data-glossary', code)
        emphasis = renderer.text('**SDK**')
        self.assertIn('data-glossary="0"', emphasis)

    def test_url_markers_do_not_change_the_link_target(self):
        renderer = builder.Renderer(sample())
        output = renderer.text('https://example.com/?q=**raw**&x==value==')
        self.assertIn('href="https://example.com/?q=**raw**&amp;x==value=="', output)
        self.assertNotIn('text-emphasis', output)
        self.assertNotIn('text-highlight', output)
        self.assertNotIn('<a ', renderer.text('`https://example.com/`'))

    def test_paragraphs_bullets_and_deliberate_linebreaks_keep_their_order(self):
        renderer = builder.Renderer(sample())
        output = renderer.rich({'paragraphs':['第一论点。\n该论点的条件。','第二论点。'], 'bullets':['**允许**后继续。','==拒绝==时停止。']})
        self.assertEqual(output.count('<p>'), 2)
        self.assertEqual(output.count('<li>'), 2)
        self.assertIn('第一论点。<br>该论点的条件。', output)
        self.assertLess(output.index('第一论点'), output.index('第二论点'))
        self.assertLess(output.index('第二论点'), output.index('允许'))

    def test_emphasis_in_summary_labels_does_not_create_nested_links(self):
        renderer = builder.Renderer(sample())
        output = renderer.text('**https://example.com/**', focusable=False)
        self.assertIn('text-emphasis', output)
        self.assertNotIn('<a ', output)
