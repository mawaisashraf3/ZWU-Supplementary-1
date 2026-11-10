from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import csv, json, sqlite3, re, unicodedata, hashlib

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / 'Suplementry Files'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
norm = lambda t: re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', t.lower()))
db = sqlite3.connect('file:' + str(OUT / 'Manuscript EndNote Library.Data/sdb/sdb.eni') + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
records = [dict(r) for r in db.execute('select * from refs where trash_state=0 order by id')]
mapping = list(csv.DictReader((OUT / 'Reference mapping preflight.csv').open(encoding='utf-8-sig')))
by_original = {}
for row in mapping:
    no = int(row['original_reference_number'])
    title = row['supplied_title'] if no != 146 else 'Synchronously manipulating Zn2+ transfer and hydrogen/oxygen evolution kinetics in MXene host electrodes toward symmetric Zn-ions micro-supercapacitor with enhanced areal energy density'
    matches = [r for r in records if norm(r['title']) == norm(title)]
    assert matches, (no, title)
    by_original[no] = matches[0]
assert len({r['id'] for r in by_original.values()}) == 209

def temporary(nums):
    result = []
    for num in dict.fromkeys(nums):
        r = by_original[num]
        author = r['author'].split('\r')[0].split(',')[0]
        result.append(f"{author}, {r['year']} #{r['id']}")
    return '{' + '; '.join(result) + '}'

def text(p):
    return ''.join(p.xpath('.//w:t/text()', namespaces=NS))

def replace_range(p, start, end, inserted):
    nodes = p.xpath('.//w:t', namespaces=NS)
    pos = 0
    started = False
    for n in nodes:
        old = n.text or ''
        nend = pos + len(old)
        if start < nend and end > pos:
            a = max(start - pos, 0)
            b = min(end - pos, len(old))
            n.text = old[:a] + (inserted if not started else '') + old[b:]
            n.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            started = True
        pos = nend
    assert started, (start, end)

with ZipFile(BASE / 'R7- Manuscript.docx') as z:
    package = {n: z.read(n) for n in z.namelist()}
root = E.fromstring(package['word/document.xml'])
pars = root.xpath('//w:body//w:p', namespaces=NS)
ref_index = next(i for i, p in enumerate(pars) if text(p) == 'References')
assert ref_index == 591
assert len(pars[ref_index+1:]) == 209
for i,p in enumerate(pars[ref_index+1:],1):
    assert re.match(r'\['+str(i)+r'\]', text(p))
    assert not p.xpath('.//w:drawing|.//w:object', namespaces=NS)

group_re = re.compile(r'\[\d+\](?:\s*(?:,|[–−-])\s*\[\d+\])*')
changes=[]
used=set()
for pi,p in enumerate(pars[:ref_index]):
    original = text(p)
    for match in reversed(list(group_re.finditer(original))):
        cluster = match.group()
        tokens = list(re.finditer(r'\[(\d+)\]', cluster))
        nums=[]
        for j,tok in enumerate(tokens):
            num = int(tok[1])
            assert 1 <= num <= 209
            if j and re.search(r'[–−-]', cluster[tokens[j-1].end():tok.start()]):
                assert num >= int(tokens[j-1][1])
                nums.extend(range(int(tokens[j-1][1])+1,num+1))
            else: nums.append(num)
        corrected = [36 if pi in (73,79) and n==59 else 199 if pi==470 and n==198 else n for n in nums]
        used.update(corrected)
        changes.append({'paragraph_index':pi,'original_marker':cluster,'original_numbers':nums,'linked_original_numbers':corrected,'endnote_record_ids':[by_original[n]['id'] for n in dict.fromkeys(corrected)],'action':'corrected source link' if corrected!=nums else 'converted existing citation'})
        replace_range(p,match.start(),match.end(),temporary(corrected))

# Add the two previously uncited, supplied sensor reviews at the matching mechanism statement.
p = pars[436]
anchor = 'Applied strain and pressure modify conductive pathways between MXene nanosheets, producing measurable resistance or capacitance variations.'
current = text(p)
assert current.count(anchor) == 1
at = current.index(anchor)+len(anchor)
# Replace the sentence-ending period with itself plus the citation; sentence words remain untouched.
replace_range(p,at-1,at,' '+temporary([208,209])+'.')
used.update([208,209])
changes.append({'paragraph_index':436,'original_marker':'','original_numbers':[],'linked_original_numbers':[208,209],'endnote_record_ids':[by_original[n]['id'] for n in (208,209)],'action':'added supplied reviews at strain/pressure transduction statement; verified publisher abstracts'})
assert used == set(range(1,210)), sorted(set(range(1,210))-used)

for p in pars[ref_index+1:]: p.getparent().remove(p)
package['word/document.xml'] = E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
with ZipFile(OUT / 'Citation preparation.docx','w',compression=ZIP_DEFLATED) as z:
    for n,b in package.items():z.writestr(n,b)
(OUT / 'Citation insertion log.json').write_text(json.dumps(sorted(changes,key=lambda x:x['paragraph_index']),ensure_ascii=False,indent=2),encoding='utf8')
(OUT / 'EndNote record mapping.json').write_text(json.dumps({str(n):{k:r[k] for k in ['id','author','year','title','secondary_title','volume','number','pages','electronic_resource_number']} for n,r in by_original.items()},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'citation_groups':len(changes),'distinct_references':len(used),'temporary_citations':sum(text(p).count('{') for p in pars[:ref_index]),'source_sha256':hashlib.sha256((BASE/'R7- Manuscript.docx').read_bytes()).hexdigest()}))
