import copy
import re
import unittest
from html.parser import HTMLParser

from test_builder import builder, sample, render


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections = []
        self.current = None
        self.ids = {}
        self.refs = []
        self.nav = False
        self.nav_depth = 0
        self.nav_hrefs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'section':
            self.sections.append(self.current)
            if 'data-chapter' in a: self.current = a['id']
        if 'id' in a:
            if a['id'] in self.ids: raise AssertionError('duplicate id: ' + a['id'])
            self.ids[a['id']] = self.current
        if tag == 'aside' and a.get('id') == 'report-outline': self.nav = True
        if self.nav and tag == 'a': self.nav_hrefs.append(a['href'])
        if a.get('class') == 'evidence-ref': self.refs.append((self.current, a['href'][1:]))

    def handle_endtag(self, tag):
        if tag == 'section': self.current = self.sections.pop()
        if tag == 'aside': self.nav = False


def focused():
    data = sample()
    del data['readingMode']
    data['findings'] = []
    data['responsibilities'] = []
    data['verdict']['summary'] = '源码有入口。[[证据一]]'
    data['sections'][0].update(title='接法', subtitle='推荐怎么接？', evidence=['证据一'], folds=[{'title':'字段明细','items':['可核对']}])
    data['sections'][1]['rows'][0][1] = '已登记入口。[[证据一]]'
    return data


class FocusTests(unittest.TestCase):
    def test_custom_chinese_evidence_category_is_preserved_in_complete_inventory(self):
        data=focused();data['evidence'][0]['level']='设计笔记'
        output=render(data)
        table=output.split('class="content-table evidence-table"',1)[1].split('</table>',1)[0]
        self.assertIn('设计笔记',table)
        self.assertNotIn('其他证据',table)
        data['evidence'][0]['level']='unknown-vendor-kind'
        table=render(data).split('class="content-table evidence-table"',1)[1].split('</table>',1)[0]
        self.assertIn('其他证据',table)

    def test_overview_uses_current_section_summary_and_preserves_observed_progress(self):
        data=focused()
        data['verdict']['topics']=['chain','changes']
        data['sections'][0]['summary']='改后的唯一一句话结论[[证据一]]'
        data['sections'][1]['summary']='第二项结论'
        data['verdict']['progress']=[{'title':'本地检查','status':'历史通过','summary':'本轮未复测','evidence':['证据一']},{'title':'目标环境','status':'未知','summary':'没有执行记录'}]
        output=render(data)
        core=output.split('id="overview"',1)[1].split('id="chain"',1)[0]
        for text in ('改后的唯一一句话结论','第二项结论','历史通过','本轮未复测','未知','没有执行记录'):
            self.assertIn(text,core)
        self.assertIn('href="#chain"',core)
        self.assertNotIn('type="checkbox"',core)
        data['sections'][0]['summary']='新的单一事实源'
        core=render(data).split('id="overview"',1)[1].split('id="chain"',1)[0]
        self.assertIn('新的单一事实源',core)
        self.assertNotIn('改后的唯一一句话结论',core)

    def test_overview_rejects_missing_duplicate_or_unexplained_topics(self):
        for topics in (['absent'],['chain','chain'],['chain']):
            data=focused();data['verdict']['topics']=topics
            with self.subTest(topics=topics),self.assertRaisesRegex(ValueError,'topics'):
                render(data)
        data=focused();data['verdict']['topics']=['chain'];data['sections'][0]['summary']='  '
        with self.assertRaisesRegex(ValueError,'topics'):render(data)

    def test_sources_are_only_links_while_complete_records_remain_in_appendix(self):
        output=render(focused())
        footers=re.findall(r'<aside class="section-sources".*?</aside>',output,re.S)
        self.assertTrue(footers)
        for footer in footers:
            self.assertNotIn('尚未进行真实联调',footer)
            self.assertNotIn('源码存在结果处理入口',footer)
            self.assertNotIn('<details',footer)
        appendix=output.split('<section class="section" id="appendix"',1)[1].split('</section>',1)[0]
        self.assertIn('源码存在结果处理入口',appendix)
        self.assertIn('尚未进行真实联调',appendix)

    def test_highlights_and_progress_validate_real_targets_and_explicit_states(self):
        data=focused();data['highlights']=[{'label':'下一步','value':'接通首条链路','target':'chain'}]
        self.assertFalse(builder.unknown_fields(data))
        self.assertIn('class="nav-highlights"',render(data))
        data['highlights'][0]['target']='absent'
        with self.assertRaisesRegex(ValueError,'target'):render(data)
        for progress in ([{'title':'验收'}],['完成']):
            data=focused();data['verdict']['progress']=progress
            with self.assertRaises(ValueError):render(data)

    def test_default_focus_keeps_all_content_but_only_top_level_navigation(self):
        output = render(focused())
        doc = Document(); doc.feed(output)
        self.assertIn('data-reading-mode="focus"', output)
        self.assertEqual(doc.nav_hrefs, ['#overview','#chain','#changes','#appendix'])
        for text in ('字段明细','可核对','推荐怎么接？'): self.assertIn(text, output)
        outline = output.split('<aside class="report-outline',1)[1].split('</aside>',1)[0]
        self.assertIn('推荐怎么接', outline)
        self.assertNotIn('字段明细', outline)
        self.assertNotIn('id="evidence-layers"', output)

    def test_subtitle_help_is_beside_navigation_and_retains_static_reading(self):
        output = render(focused())
        outline = output.split('<aside class="report-outline', 1)[1].split('</aside>', 1)[0]
        self.assertRegex(outline, r'</a><span class="heading-note nav-note"><button')
        self.assertIn('aria-expanded="false"', outline)
        heading = re.search(r'id="chain"[^>]*>.*?</h2>', output, re.S).group()
        self.assertNotIn('heading-help', heading)
        self.assertIn('class="section-subtitle nav-subtitle">推荐怎么接？</p>', output)
        data = focused(); data['readingMode'] = 'continuous'
        self.assertNotIn('nav-note', render(data).split('</aside>', 1)[0].split('<body', 1)[1])

    def test_status_attention_does_not_treat_history_or_pending_as_complete(self):
        cases = {'历史通过':'reference', '待实施':'action', '待验收':'review',
                 '未知':'review', '受阻':'critical', '已完成':'confirmed',
                 '历史未通过':'reference', 'partial':'review', 'unverified':'review'}
        for status, attention in cases.items():
            with self.subTest(status=status):
                data = focused(); data['verdict']['progress'] = [{'title':'事项','status':status}]
                core = render(data).split('class="overview-progress"', 1)[1].split('</section>', 1)[0]
                self.assertIn(f'data-attention="{attention}"', core)
                self.assertIn(builder.Renderer(data, None).status(status), core)

    def test_citations_target_sources_in_their_own_chapter(self):
        output = render(focused())
        doc = Document(); doc.feed(output)
        self.assertGreaterEqual(len(doc.refs), 3)
        for section, target in doc.refs:
            self.assertEqual(section, doc.ids[target])
        self.assertIn('源码有入口。<sup', output)
        self.assertIn('已登记入口。<sup', output)
        self.assertEqual(len(set(target for _,target in doc.refs)), 3)
        self.assertNotIn('>证据一</a>', output)

    def test_inline_citation_validation_ignores_literal_code(self):
        data = focused()
        data['verdict']['summary'] = '`[[不存在]]` 是代码；真实引用[[证据一]]。'
        output = render(data)
        self.assertIn('<code class="inline-code">[[不存在]]</code>', output)
        data['verdict']['summary'] = '未知断言[[不存在]]'
        with self.assertRaisesRegex(ValueError,'不存在的证据'): render(data)

    def test_citation_numbers_are_global_not_per_chapter(self):
        data = focused()
        data['evidence'].insert(0, dict(data['evidence'][0],id='先登记',summary='另一个来源'))
        output = render(data)
        refs = re.findall(r'class="evidence-ref"[^>]*>\[(\d+)\]', output)
        self.assertTrue(refs)
        self.assertEqual(set(refs), {'2'})

    def test_new_fields_pass_strict_but_bad_modes_and_missing_diagrams_fail(self):
        data = focused()
        data['sections'][0]['navTitle'] = '接法'
        self.assertFalse(builder.unknown_fields(data))
        for mutation in ({'readingMode':'popup'}, {'verdict':dict(data['verdict'],diagramId='absent')}):
            bad=copy.deepcopy(data); bad.update(mutation)
            with self.assertRaises(ValueError): render(bad)

    def test_previously_unreachable_component_text_checks_run(self):
        data = focused()
        data['components'] = [{'id':'c','title':'组件','body':['must not render as list repr']}]
        with self.assertRaisesRegex(ValueError,'文本'): render(data)

    def test_explicit_layers_remain_available_without_anchor_collisions(self):
        data = focused()
        data['evidenceLayers'] = [{'level':'SOURCE_BUILD','status':'not_run','reason':'只登记来源','evidence':['证据一']}]
        output = render(data)
        doc = Document(); doc.feed(output)
        self.assertIn('#evidence-layers', doc.nav_hrefs)
        for _, target in doc.refs: self.assertIn(target, doc.ids)

    def test_sources_can_cite_other_sources_without_dangling_anchors(self):
        data = focused()
        data['evidence'].append(dict(data['evidence'][0],id='补充',summary='补充记录'))
        data['evidence'][0]['items']=[{'body':'参见补充[[补充]]'}]
        output=render(data)
        doc=Document(); doc.feed(output)
        for section,target in doc.refs: self.assertEqual(section, doc.ids[target])


if __name__ == '__main__': unittest.main()
