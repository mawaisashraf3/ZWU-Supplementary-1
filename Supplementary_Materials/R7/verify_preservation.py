from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from collections import Counter
import base64, re, json, hashlib, sys
BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'Suplementry Files'
target=Path(sys.argv[1]) if len(sys.argv)>1 else OUT/'Citation preparation.docx'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W='{'+ns['w']+'}'
tx=lambda p:''.join(p.xpath('.//w:t/text()',namespaces=ns))
rx=re.compile(r'\[\d+\](?:\s*(?:,|[–−-])\s*\[\d+\])*')
def outside_fields(p):
    result=[];depth=0
    for n in p.iter():
        if n.tag==W+'fldChar':
            typ=n.get(W+'fldCharType')
            if typ=='begin':depth+=1
            elif typ=='end':depth-=1
        elif n.tag==W+'t' and depth==0:result.append(n.text or '')
    assert depth==0
    return ''.join(result)
def logical(e):
    if e is None:return None
    attrs=tuple(sorted((k,v) for k,v in e.attrib.items() if 'rsid' not in k and 'paraId' not in k and 'textId' not in k))
    return e.tag,attrs,(e.text or '').strip(),tuple(logical(c) for c in e)
with ZipFile(BASE/'R7- Manuscript.docx') as a,ZipFile(target) as f:
    ra=E.fromstring(a.read('word/document.xml'));rf=E.fromstring(f.read('word/document.xml'))
    pa=ra.xpath('//w:body//w:p',namespaces=ns);pf=rf.xpath('//w:body//w:p',namespaces=ns)
    ia=next(i for i,p in enumerate(pa) if tx(p)=='References');fi=next(i for i,p in enumerate(pf) if tx(p)=='References')
    assert ia==fi==591
    differences=[]
    for i,(oa,of) in enumerate(zip(pa[:ia],pf[:fi])):
        ta=rx.sub('',tx(oa));tf=outside_fields(of)
        if i==436:tf=tf.replace('variations .','variations.')
        if ta!=tf:differences.append(i)
    media=[n for n in a.namelist() if n.startswith('word/media/')]
    assert all(a.read(n)==f.read(n) for n in media)
    def counts(r):return {n:len(r.xpath(q,namespaces=ns)) for n,q in [('tables','//w:tbl'),('drawings','//w:drawing'),('sections','//w:sectPr'),('equations','//*[local-name()="oMath"]')]}
    props_diffs=[i for i,(x,y) in enumerate(zip(pa[:ia],pf[:fi])) if logical(x.find('w:pPr',ns))!=logical(y.find('w:pPr',ns))]
    math_same=[logical(x) for x in ra.xpath('//*[local-name()="oMath"]')]==[logical(x) for x in rf.xpath('//*[local-name()="oMath"]')]
    sections_same=[logical(x) for x in ra.xpath('//w:sectPr',namespaces=ns)]==[logical(x) for x in rf.xpath('//w:sectPr',namespaces=ns)]
    tables_same=[logical(x.find('w:tblPr',ns)) for x in ra.xpath('//w:tbl',namespaces=ns)]==[logical(x.find('w:tblPr',ns)) for x in rf.xpath('//w:tbl',namespaces=ns)]
    instructions=rf.xpath('//w:instrText/text()',namespaces=ns)
    endnote_xml=[]
    for code in instructions:
        at=code.find('<EndNote>')
        if at>=0:endnote_xml.append(code[at:code.rfind('</EndNote>')+len('</EndNote>')])
    for s in rf.xpath('//w:fldData/text()',namespaces=ns):
        b=base64.b64decode(s).rstrip(b'\x00')
        if b.startswith(b'<EndNote>'):endnote_xml.append(b.decode('utf8'))
    records={};rec_counts=Counter()
    for xml in endnote_xml:
        root=E.fromstring(xml.encode('utf8'))
        for cite in root.findall('Cite'):
            number=cite.findtext('RecNum');r=cite.find('record')
            if number and r is not None:
                number=int(number);rec_counts[number]+=1
                records[number]={'title':r.findtext('titles/title'),'year':r.findtext('dates/year'),'library_key':r.findtext('foreign-keys/key')}
    expected=json.loads((OUT/'EndNote record mapping.json').read_text(encoding='utf8'))
    wanted={v['id']:v for v in expected.values()}
    mismatched=[n for n in records if n not in wanted or records[n]['title']!=wanted[n]['title'] or records[n]['year']!=wanted[n]['year']]
    refs=[tx(p) for p in pf[fi+1:] if re.match(r'^\d+\.',tx(p))]
    refnums=[int(re.match(r'^(\d+)\.',t)[1]) for t in refs]
    settings=E.fromstring(f.read('word/settings.xml'))
    layout=settings.xpath('//w:docVar[@w:name="EN.Layout"]/@w:val',namespaces=ns)[0]
    report={'target':target.name,'original_sha256':hashlib.sha256((BASE/'R7- Manuscript.docx').read_bytes()).hexdigest(),'noncitation_text_differences':differences,'body_paragraph_count':ia,'paragraph_property_differences':props_diffs,'source_counts':counts(ra),'final_counts':counts(rf),'media_files':len(media),'media_byte_identical':True,'equations_identical':math_same,'section_layout_properties_identical':sections_same,'table_properties_identical':tables_same,'endnote_cite_instructions':sum(bool(re.match(r'\s*ADDIN EN\.CITE\s*(?:<|$)',c)) for c in instructions),'endnote_data_instructions':sum('EN.CITE.DATA' in c for c in instructions),'linked_bibliography_fields':sum('EN.REFLIST' in c for c in instructions),'unique_cited_records':len(records),'missing_cited_record_ids':sorted(set(wanted)-records.keys()),'citation_metadata_mismatches':mismatched,'bibliography_entries':len(refs),'bibliography_numbers_sequential':refnums==list(range(1,210)),'numbered_style':'<Style>Numbered</Style>' in layout,'remaining_temporary_citations':bool(re.search(r'\{[^}]*#\d+[^}]*\}', ''.join(tx(p) for p in pf[:fi])))}
    (OUT/'Final preservation and linkage verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'Embedded EndNote records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    assert not differences and not mismatched
    assert counts(ra)==counts(rf) and math_same and sections_same and tables_same
    assert len(records)==209 and not report['missing_cited_record_ids']
    assert len(refs)==209 and report['bibliography_numbers_sequential'] and report['numbered_style']
    assert report['linked_bibliography_fields']==1 and not report['remaining_temporary_citations']
