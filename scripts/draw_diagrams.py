"""Hand-authored SVG layout in a clean white architecture-diagram style.

Data nodes/edges match setup_bigquery.py. Execution nodes/edges match workflow.py.
The Together view deliberately shows only A-1043's manual-review route.
"""
from html import escape

from app.config import ROOT

STYLE = '''<style>
text{font-family:-apple-system,"SF Pro Text","Helvetica Neue",Arial,sans-serif;fill:#0F172A}
.mono{font-family:"SF Mono",Menlo,Consolas,monospace}.title{font-size:34px;font-weight:700}
.sub{font-size:20px;fill:#64748B}.lbl{font-size:16px;fill:#64748B}.tag{font-size:18px;font-weight:600;fill:#334155}
</style><defs>
<linearGradient id="agent"><stop stop-color="#6366F1"/><stop offset="1" stop-color="#8B5CF6"/></linearGradient>
<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#94A3B8"/></marker>
</defs>'''


def text(x, y, value, cls='', size=None, color=None, anchor='start'):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}"' + (f' font-size="{size}"' if size else '') + (f' style="fill:{color}"' if color else '') + f'>{escape(value)}</text>'


def node(key, x, y, w, h, title, lines=(), kind='function'):
    fill, border, color = {
        'function': ('#FFFFFF', '#94A3B8', '#0F172A'),
        'data': ('#FFFFFF', '#F59E0B', '#0F172A'),
        'rule': ('#FFFFFF', '#10B981', '#047857'),
        'human': ('#FFFBEB', '#F59E0B', '#92400E'),
        'model': ('url(#agent)', '#8B5CF6', '#FFFFFF'),
    }[kind]
    out = f'<g data-node="{key}" role="button" tabindex="0" aria-label="{escape(title)}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{border}" stroke-width="2"/>'
    out += text(x+w/2, y+34, ('✦ ' if kind == 'model' else '')+title, 'mono', 20, color, 'middle')
    for i, line in enumerate(lines):
        out += f'<text data-value="{key}-{i}" x="{x+w/2}" y="{y+61+i*24}" text-anchor="middle" font-size="16" style="fill:{color};opacity:.78">{escape(line)}</text>'
    return out+'</g>'


def arrow(path, label='', x=0, y=0, dashed=False):
    return f'<path d="{path}" fill="none" stroke="#94A3B8" stroke-width="2" marker-end="url(#arr)"'+(' stroke-dasharray="7 5"' if dashed else '')+'/>'+ (text(x,y,label,'mono lbl',anchor='middle') if label else '')


def step(n, x, y):
    return f'<circle cx="{x}" cy="{y}" r="15" fill="#0F172A"/>' + text(x,y+5,str(n),'',14,'#FFFFFF','middle')


def container(x,y,w,h,label):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#F8FAFC" fill-opacity=".6" stroke="#94A3B8" stroke-width="2" stroke-dasharray="8 6"/>'+text(x+25,y+34,label,'mono tag')


def legend(y):
    out=''
    for i,(label,fill,stroke) in enumerate([
        ('Data record','#FFFFFF','#F59E0B'), ('Function','#FFFFFF','#94A3B8'),
        ('Policy','#FFFFFF','#10B981'), ('Reviewer','#FFFBEB','#F59E0B'),
        ('Model','url(#agent)','#8B5CF6'),
    ]):
        x=70+i*170
        out+=f'<rect x="{x}" y="{y-12}" width="13" height="13" rx="3" fill="{fill}" stroke="{stroke}"/>'
        out+=text(x+22,y,label,'',14,'#64748B')
    return out


def start(title, sub, height):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="{height}" viewBox="0 0 1600 {height}">' + STYLE + f'<rect width="1600" height="{height}" fill="#FFFFFF"/>' + text(70,75,title,'title') + text(70,115,sub,'sub')


def save(name, content):
    path = ROOT/'static'/'diagrams'
    path.mkdir(parents=True, exist_ok=True)
    (path/f'{name}.svg').write_text(content+'</svg>')


def main():
    s=start('The data graph connects the facts', 'One case, four records. Arrows describe relationships stored in BigQuery.', 650)
    s+=container(70,160,1460,440,'BIGQUERY · RefundGraph')
    s+=arrow('M450 270 H660','PLACED',555,249)
    s+=arrow('M950 270 H1160','HAS_PAYMENT',1055,249)
    s+=arrow('M305 325 V445','HAS_HISTORY',415,392)
    s+=node('customer',160,215,290,110,'Customer',['Account age: 412 days'],kind='data')
    s+=node('order',660,215,290,110,'Order A-1043',['$62 · 12 days ago','Trail running shoes'],kind='data')
    s+=node('payment',1160,215,290,110,'Payment',['Visa · settled','No open chargeback'],kind='data')
    s+=node('history',160,445,290,100,'Refund history',['1 prior refund · 12 months'],kind='data')
    s+=text(660,470,'Start at the order. Follow its payment,','sub')+text(660,502,"then its customer's history summary.",'sub')
    s+=text(660,548,'No prior transaction details were invented.','lbl')
    save('data',s)

    s=start('The workflow controls what happens next', 'Three live reads → wait for all → apply policy → review when required → draft a response.', 760)
    s+=container(70,135,1460,510,'ADK WORKFLOW · Python')
    s+=text(100,374,'A-1043','mono',18)
    s+=arrow('M168 368 H190 V224 H215')+arrow('M168 368 H215')+arrow('M190 368 V524 H215')
    for key,y,label in [('fetch_order',180,'Order facts'),('fetch_payment',330,'Payment facts'),('fetch_history',480,'History summary')]:
        s+=node(key,215,y,235,88,key,[label])
        cy=y+44
        s+=arrow(f'M450 {cy} H490 V374 H535')
    s+=text(492,200,'results','lbl',anchor='middle')
    s+=node('join_case',535,330,160,88,'JoinNode',['Wait for all'])
    s+=arrow('M695 374 H775','case',735,353)
    s+=node('route_refund',775,330,170,88,'Policy',['Python rules'],kind='rule')
    s+=arrow('M945 374 H1060','REVIEW',1002,353)
    s+=node('human_review',1060,330,200,88,'⏸ Review',['Pause for input'],kind='human')
    s+=arrow('M860 330 V209 H1310','AUTO_APPROVE',1100,190)
    s+=arrow('M860 418 V544 H1310','DENY',1100,525)
    s+=arrow('M1260 374 H1285 V209 H1310','approve',1300,285,True)
    s+=arrow('M1285 374 V544 H1310','decline',1300,465,True)
    s+=node('approve_notice',1310,165,220,88,'Approval draft',['Selected model node'],kind='model')
    s+=node('denial_notice',1310,500,220,88,'Decline draft',['Selected model node'],kind='model')
    s+=legend(680)
    s+=text(70,720,'The original $62 case takes the review branch. A decision does not execute a payment.','lbl')
    save('workflow',s)

    s=start('The workflow queries the data graph', "The same order, end to end. This view follows A-1043's manual-review route.",930)
    s+=container(70,170,1460,250,'LOCAL APP · ADK WORKFLOW · :8765')
    s+=node('fetch_group',100,260,260,105,'Three fetch nodes',['Order · payment · history'])
    s+=node('join_case',480,260,170,105,'JoinNode',['Wait for all'])
    s+=node('route_refund',755,260,170,105,'Policy',['MANUAL_REVIEW'],kind='rule')
    s+=node('human_review',1030,260,200,105,'⏸ Review',['Pause / resume'],kind='human')
    s+=node('draft_group',1320,260,185,105,'Write reply',['Selected branch'],kind='model')
    for a,b,label in [(360,480,'records'),(650,755,'case'),(925,1030,'route'),(1230,1320,'decision')]:
        s+=arrow(f'M{a} 312 H{b}',label,(a+b)/2,292,dashed=a==1230)
    s+=container(70,535,1460,285,'GOOGLE CLOUD · BIGQUERY RefundGraph')
    s+=arrow('M175 365 V535','GQL queries',123,475)
    s+=arrow('M290 535 V365','matched records',400,475)
    for n,x,y in [(1,175,430),(2,290,430),(3,420,312),(4,702,312),(5,977,312),(6,1275,312)]:
        s+=step(n,x,y)
    s+=node('history',100,665,250,100,'Refund history',['1 prior refund · 12 months'],kind='data')
    s+=node('customer',500,665,250,100,'Customer',['Account age: 412 days'],kind='data')
    s+=node('order',915,665,250,100,'Order A-1043',['$62 · 12 days ago'],kind='data')
    s+=node('payment',1300,665,200,100,'Payment',['Visa · settled'],kind='data')
    s+=arrow('M500 715 H350','HAS_HISTORY',425,695)
    s+=arrow('M750 715 H915','PLACED',832,695)
    s+=arrow('M1165 715 H1300','HAS_PAYMENT',1232,695)
    s+=legend(855)
    s+=text(70,895,'Data edges connect records. Workflow edges connect steps. The query is where the two meet.','lbl')
    save('together',s)
    print('Wrote three diagrams matching the implemented schema and Workflow.')


if __name__ == '__main__':
    main()

