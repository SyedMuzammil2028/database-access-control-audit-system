"""Build the academic submission using the bundled document/PDF runtime.
Run schema export first (see docs/submission/README.md). No database writes.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import json, math
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.section import WD_SECTION_START, WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/submission'; QA=ROOT/'artifacts/submission-qa'
OUT.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
SCHEMA=json.loads((OUT/'schema_snapshot.json').read_text()); TABLES={t['name']:t for t in SCHEMA}
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
pdfmetrics.registerFont(TTFont('DejaVu',FONT));pdfmetrics.registerFont(TTFont('DejaVu-Bold',BOLD))
INK=HexColor('#17212e');GRAY=HexColor('#586574');BORDER=HexColor('#b3bfca');HEADER=HexColor('#e8eef4');BLUE=HexColor('#31536e')
W,H=landscape(A4)

def text(c,x,y,s,size=9,bold=False,color=INK):
 c.setFont('DejaVu-Bold' if bold else 'DejaVu',size);c.setFillColor(color);c.drawString(x,y,s)


def draw_table(c,name,x,top,width=220,ref=False):
 t=TABLES[name];rows=t['columns'] if not ref else [col for col in t['columns'] if col['pk']]
 height=29+len(rows)*17+10
 c.setFillColor(white);c.setStrokeColor(BORDER);c.setLineWidth(.8);c.rect(x,top-height,width,height,fill=1,stroke=1)
 c.setFillColor(HEADER);c.rect(x,top-27,width,27,fill=1,stroke=0)
 text(c,x+10,top-18,name.upper()+('  [reference]' if ref else ''),9.5,True)
 ports={}
 for i,col in enumerate(rows):
  y=top-42-i*17
  marker='PK' if col['pk'] else ''
  if col['fk']:marker=marker+'/FK' if marker else 'FK'
  text(c,x+9,y,marker,7.1,True,BLUE)
  field=col['name']+(' ?' if col['nullable'] else '')
  text(c,x+48,y,field,8.2)
  typ=col['type'].replace('VARCHAR','V').replace('TIMESTAMP','timestamptz').replace('DATETIME','timestamptz').replace('INTEGER','int').replace('BOOLEAN','bool')
  if len(typ)>16:typ=typ[:16]
  text(c,x+width-82,y,typ,7,color=GRAY)
  ports[col['name']]=(x,y+3,x+width)
 return {'x':x,'top':top,'w':width,'bottom':top-height,'ports':ports}


def edge(c,child,field,parent,label,side='left',track=None):
 a=child['ports'][field];b=parent['ports'][next(iter(parent['ports']))]
 if side=='left':
  sx,sy=a[0],a[1];ex,ey=b[2],b[1];mid=track if track is not None else (sx+ex)/2
  pts=[(sx,sy),(mid,sy),(mid,ey),(ex,ey)]
 elif side=='right':
  sx,sy=a[2],a[1];ex,ey=b[0],b[1];mid=track if track is not None else (sx+ex)/2
  pts=[(sx,sy),(mid,sy),(mid,ey),(ex,ey)]
 else:
  sx,sy=child['x']+child['w']*.5,child['top'];ex,ey=parent['x']+parent['w']*.5,parent['bottom'];mid=track or (sy+ey)/2
  pts=[(sx,sy),(sx,mid),(ex,mid),(ex,ey)]
 c.setStrokeColor(BLUE);c.setLineWidth(.9)
 path=c.beginPath();path.moveTo(*pts[0])
 for p in pts[1:]:path.lineTo(*p)
 c.drawPath(path)
 # FK -> PK arrowhead; cardinality separately printed as mandatory/optional legend.
 dx,dy=pts[-1][0]-pts[-2][0],pts[-1][1]-pts[-2][1];length=math.hypot(dx,dy);ux,uy=dx/length,dy/length
 p=c.beginPath();p.moveTo(ex,ey);p.lineTo(ex-6*ux+3*uy,ey-6*uy-3*ux);p.moveTo(ex,ey);p.lineTo(ex-6*ux-3*uy,ey-6*uy+3*ux);c.drawPath(p)
 text(c,(pts[1][0]+pts[2][0])/2+4,(pts[1][1]+pts[2][1])/2+5,label,6.5,color=BLUE)


def diagram_page(c,title,subtitle,num):
 c.setFillColor(white);c.rect(0,0,W,H,fill=1,stroke=0)
 text(c,27,H-34,title,17,True);text(c,27,H-53,subtitle,8.3,color=GRAY)
 c.setStrokeColor(BORDER);c.line(27,53,W-27,53)
 text(c,27,38,'PK primary key   FK foreign key   ? nullable   V(n) varchar(n)   Arrows point from FK to referenced PK',7.4,color=GRAY)
 text(c,27,24,'Mandatory FK: each child has 1 parent; nullable FK: 0 or 1. Every parent can have 0..many children.',7.1,color=GRAY)
 text(c,W-90,24,f'ER diagram {num}/3',7.2,color=GRAY)


def build_erd():
 path=OUT/'ER_Diagram.pdf';c=canvas.Canvas(str(path),pagesize=(W,H));c.setTitle('Database Access Control and Audit System Complete ER Diagram')
 diagram_page(c,'Role based access control model','Five policy entities - both many-to-many relationships are resolved by composite-key junction tables.',1)
 u=draw_table(c,'app_user',28,510,245);ur=draw_table(c,'user_role',326,510,230);r=draw_table(c,'role',610,510,204)
 rp=draw_table(c,'role_permission',326,270,230);p=draw_table(c,'permission',610,270,204)
 edge(c,ur,'user_id',u,'subject',track=288);edge(c,ur,'assigned_by',u,'administrator',track=306)
 edge(c,ur,'role_id',r,'assigned role','right',track=579)
 edge(c,rp,'role_id',r,'role','up',track=322)
 edge(c,rp,'permission_id',p,'permission','right',track=580)
 text(c,28,215,'Candidate keys and business rules',9,True)
 for i,line in enumerate(['APP_USER email is unique and lowercase.','ROLE name is unique; kind is admin, auditor or user.','PERMISSION UNIQUE(action, resource_type).','USER_ROLE PK(user_id, role_id); revocations set active=false.','ROLE_PERMISSION PK(role_id, permission_id).']):text(c,28,195-i*20,line,7.8)
 c.showPage()
 diagram_page(c,'Resource and historical audit model','Historical strings are event snapshots. Policy targets identify past changes rather than polymorphic foreign keys.',2)
 u=draw_table(c,'app_user',28,510,230,True);r=draw_table(c,'role',28,418,230,True)
 resource=draw_table(c,'resource',28,320,250);ae=draw_table(c,'audit_event',338,510,288);pc=draw_table(c,'policy_change',650,510,164)
 # Narrow policy box uses compact custom redraw for long field names.
 c.setFillColor(white);c.rect(650,pc['bottom'],164,510-pc['bottom'],fill=1,stroke=0)
 pc=draw_table(c,'policy_change',650,510,164)
 # Redraw policy row text in condensed columns to avoid overlap.
 c.setFillColor(white);c.rect(652,pc['bottom']+2,160,510-29-(pc['bottom']+2),fill=1,stroke=0)
 for i,col in enumerate(TABLES['policy_change']['columns']):
  yy=510-42-i*17;text(c,657,yy,('PK ' if col['pk'] else 'FK ' if col['fk'] else '')+col['name'],7.4)
 # Route owner relationship outside the repeated ROLE box.
 c.setStrokeColor(BLUE);path=c.beginPath();owner_y=resource['ports']['owner_user_id'][1];path.moveTo(28,owner_y);path.lineTo(16,owner_y);path.lineTo(16,u['ports']['id'][1]);path.lineTo(28,u['ports']['id'][1]);c.drawPath(path)
 c.line(28,u['ports']['id'][1],22,u['ports']['id'][1]+3);c.line(28,u['ports']['id'][1],22,u['ports']['id'][1]-3)
 text(c,29,330,'owner -> APP_USER.id (mandatory)',7,color=BLUE)
 edge(c,ae,'actor_user_id',u,'actor 0..1','left',track=297)
 edge(c,ae,'matching_role_id',r,'match 0..1','left',track=311)
 edge(c,ae,'resource_id',resource,'resource 0..1','left',track=324)
 # Policy actor path above tables with explicit source/target; no invented target FK.
 c.setStrokeColor(BLUE);path=c.beginPath();sx,sy=pc['ports']['actor_user_id'][:2];path.moveTo(sx,sy);path.lineTo(639,sy);path.lineTo(639,529);path.lineTo(144,529);path.lineTo(144,510);c.drawPath(path)
 c.line(144,510,141,516);c.line(144,510,147,516)
 text(c,340,533,'POLICY_CHANGE.actor_user_id -> APP_USER.id (mandatory)',6.7,color=BLUE)
 text(c,28,125,'Integrity and history',9,True)
 for i,line in enumerate(['RESOURCE UNIQUE(resource_type, resource_key). AUDIT_EVENT UNIQUE(actor_user_id, request_id).',
  'ALLOWED requires reason ALLOWED_BY_ROLE and a recorded matching role; DENIED has no matching role.',
  'Policy target_type/target_id and JSON details preserve deleted mapping identifiers; they are not foreign keys.']):text(c,28,105-i*16,line,7.6)
 c.showPage()
 diagram_page(c,'Authentication support and relationship inventory','Two technical entities support revocable sessions and authentication investigation; they do not replace core RBAC.',3)
 u=draw_table(c,'app_user',28,510,235,True);ls=draw_table(c,'login_session',330,510,230);se=draw_table(c,'security_event',330,338,230)
 edge(c,ls,'user_id',u,'session user','left',track=285);edge(c,se,'actor_user_id',u,'actor 0..1','left',track=305)
 text(c,594,488,'All twelve foreign keys',10,True)
 inventory=[('user_role.user_id','app_user.id'),('user_role.role_id','role.id'),('user_role.assigned_by','app_user.id'),('role_permission.role_id','role.id'),('role_permission.permission_id','permission.id'),('resource.owner_user_id','app_user.id'),('audit_event.actor_user_id ?','app_user.id'),('audit_event.resource_id ?','resource.id'),('audit_event.matching_role_id ?','role.id'),('policy_change.actor_user_id','app_user.id'),('login_session.user_id','app_user.id'),('security_event.actor_user_id ?','app_user.id')]
 for i,(a,b) in enumerate(inventory):text(c,594,464-i*25,a,7.1);text(c,604,454-i*25,'references '+b,7,color=GRAY)
 text(c,28,231,'Data protection',9,True)
 for i,line in enumerate(['Browser: opaque HttpOnly cookie.', 'Database: SHA-256 session-token digest.', 'Passwords: salted Argon2id hashes.', 'Expiry checked on protected requests.', 'No audit edit or deletion API.', 'Authentication IP stored as a keyed hash.']):text(c,28,210-i*20,line,7.8)
 c.save();return OUT/'ER_Diagram.pdf'


def shade(cell,fill):
 tcPr=cell._tc.get_or_add_tcPr();el=OxmlElement('w:shd');el.set(qn('w:fill'),fill);tcPr.append(el)


def setup_section(s,land=False):
 s.orientation=WD_ORIENT.LANDSCAPE if land else WD_ORIENT.PORTRAIT
 s.page_width=Inches(11.69 if land else 8.27);s.page_height=Inches(8.27 if land else 11.69)
 s.top_margin=Inches(.63);s.bottom_margin=Inches(.62);s.left_margin=Inches(.72);s.right_margin=Inches(.72)
 s.header_distance=Inches(.25);s.footer_distance=Inches(.28)


doc=Document();setup_section(doc.sections[0])
for style in ['Normal','Body Text']:
 st=doc.styles[style];st.font.name='Calibri';st.font.size=Pt(10.5);st.paragraph_format.space_after=Pt(7);st.paragraph_format.line_spacing=1.12
for name,size in [('Title',28),('Subtitle',13),('Heading 1',18),('Heading 2',12),('Heading 3',10.5)]:
 st=doc.styles[name];st.font.name='Calibri';st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0);st.paragraph_format.space_after=Pt(9);st.paragraph_format.space_before=Pt(13 if name!='Title' else 0)
 st.paragraph_format.keep_with_next=True
for name in ['Heading 1','Heading 2','Heading 3']:doc.styles[name].font.bold=True
# Strip the bundled Word template title border and all theme-colored captions.
for st in doc.styles:
 for border in st.element.findall('.//' + qn('w:pBdr')):
  border.getparent().remove(border)
doc.styles['Caption'].font.color.rgb=RGBColor(0,0,0)
doc.styles['Caption'].font.size=Pt(9)
header=doc.sections[0].header.paragraphs[0];header.text='DATABASE SYSTEMS  |  ACCESS CONTROL AND AUDIT';header.style='Caption';header.runs[0].font.size=Pt(8);header.runs[0].font.color.rgb=RGBColor.from_string('586574')
footer=doc.sections[0].footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
footer.add_run('Database Access Control and Audit System  |  ')
f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');footer._p.append(f)
for r in footer.runs:r.font.size=Pt(8)


def p(txt='',style=None):return doc.add_paragraph(txt,style)
def h(txt):return doc.add_heading(txt,2)
def bullet(txt):return p(txt,'List Bullet')
def new(title,land=False):
 if bool(doc.sections[-1].orientation==WD_ORIENT.LANDSCAPE)!=land:
  s=doc.add_section(WD_SECTION_START.NEW_PAGE);setup_section(s,land)
 else:doc.add_page_break()
 doc.add_heading(title,1)
def table(headers,rows,widths=None):
 t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
 for c,txt in zip(t.rows[0].cells,headers):
  c.text=txt;shade(c,'e8eef4')
  for r in c.paragraphs[0].runs:r.bold=True
 trPr=t.rows[0]._tr.get_or_add_trPr();repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
 for idx,row in enumerate(rows):
  cells=t.add_row().cells
  for c,txt in zip(cells,row):c.text=str(txt)
  if idx%2==1:
   for c in cells:shade(c,'f5f7f9')
 for row in t.rows:
  pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
  for i,c in enumerate(row.cells):
   if widths:c.width=Inches(widths[i])
   tcPr=c._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
   for edge in ['top','left','bottom','right']:
    el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');b.append(el)
   tcPr.append(b)
   margins=OxmlElement('w:tcMar')
   for tag in ['top','bottom','left','right']:
    el=OxmlElement('w:'+tag);el.set(qn('w:w'),'90');el.set(qn('w:type'),'dxa');margins.append(el)
   tcPr.append(margins)
   for para in c.paragraphs:
    para.paragraph_format.space_after=Pt(2);para.paragraph_format.space_before=Pt(1);para.paragraph_format.line_spacing=1.05
    for run in para.runs:run.font.size=Pt(9)
 return t

def picture(path,width,caption):
 pp=p();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;run=pp.add_run();run.add_picture(str(path),width=Inches(width))
 inline=run._r.xpath('.//wp:docPr')
 if inline:inline[0].set('descr',caption)
 pp.paragraph_format.space_after=Pt(3)
 cp=p(caption,'Caption');cp.paragraph_format.space_after=Pt(9)

def code(txt):
 for line in txt.strip().splitlines():
  pp=p(line);pp.paragraph_format.space_after=Pt(0);pp.paragraph_format.line_spacing=1.0
  for run in pp.runs:run.font.name='Consolas';run.font.size=Pt(8.4)
 p()


def build_report():
 # 1 Cover
 p('DATABASE SYSTEMS','Subtitle');p();doc.add_paragraph('Database Access Control\nand Audit System','Title');p('Semester Project Report','Subtitle');p('Implemented application  Access Ledger')
 p();p('Submitted by','Heading 2');table(['Group member','Student ID'],[['Syed Muhammad Muzammil','24k-2000'],['Ali Safir Qadir','24k-2039'],['Hassan Raza','24k-2034']],[4.5,2.1])
 p();p('Submitted to  Miss Abber Gohar');p('Course  Database Systems');p('Submission copy prepared  24 November 2026')
 h('Project summary');p('Access Ledger checks whether a user may perform an operation on a registered resource. Roles determine the available permissions, and PostgreSQL stores the result of each completed check. Administrators manage access, users submit requests, and auditors review the records.')
 p('The verification run on 22 November 2026 passed 113 backend and PostgreSQL tests, 12 React component tests and 5 browser workflows. The results discussed in this report come from that run.')
 # 2 intro
 new('Project context and objectives')
 h('Introduction');p('Consider an analyst who needs to read a report but should not delete it. The application must distinguish these operations and retain an explanation of the outcome. Access Ledger handles this through a role-based policy stored in PostgreSQL. The project brings together relational modelling, SQL queries, constraints and transactions in one working application.')
 h('Problem statement');p('A permission change can be difficult to trace when each screen applies its own rules. There is a second problem with investigating old requests: the roles a user holds today may differ from the roles held when a request was made. The system therefore records both access decisions and administrative changes. This allows an auditor to examine the decision alongside the policy history.')
 h('Objectives')
 for x in ['Represent users, roles, permissions, assignments and resources with normalized relations and database-enforced integrity.','Evaluate READ, CREATE, UPDATE and DELETE using one reusable default-deny service.','Persist each completed decision with actor, resource, reason, matching role, correlation ID and server timestamp.','Commit administrative changes together with their policy records and prevent final-administrator lockout.','Provide a consistent interface and searchable, bounded reports suitable for course demonstration.']:bullet(x)
 h('Scope and boundaries');p('The project covers registered documents and reports, including the sample report R42. It checks permission to read, create, update or delete a target; it does not carry out those operations on an external file store. Resource ownership is recorded, but permission still comes from an active role. Accounts are created by administrators, and all demonstration records are fictional.')
 # 3 requirements architecture
 new('Requirements and architecture')
 table(['User category','Implemented responsibilities'],[['Administrator','Create and activate/deactivate users; maintain roles and permission mappings; assign/revoke roles; register resources; inspect policy and access history.'],['Ordinary user','View active roles and effective permissions; browse resources; submit operations; inspect results and personal access history.'],['Auditor','Search decisions, inspect historical details, review policy/sign-in history and export filtered CSV; cannot change policy or submit resource evaluations.']],[1.3,5.3])
 h('Technology and component structure');table(['Layer','Technology and responsibility'],[['Database','PostgreSQL 17; keys, constraints, indexes, JSONB snapshots and transactions.'],['Backend','Python, FastAPI, SQLAlchemy, psycopg, Pydantic and Alembic.'],['Frontend','React, TypeScript, Vite, Tailwind, Radix dialogs and Lucide icons.'],['Security','Argon2id password hashing; opaque server sessions and CSRF tokens.'],['Verification','pytest/httpx, Vitest/Testing Library and Playwright/Chromium.'],['Packaging','Docker Compose; separate setup owner and restricted web database account.']],[1.25,5.35])
 h('Request flow');p('A request starts in the React interface and reaches FastAPI on the same origin. FastAPI checks the session and, for a write, the CSRF token. It then calls the appropriate service, which reads or changes PostgreSQL through SQLAlchemy. Decision and policy records are written within these service transactions, so they are not dependent on a separate logging process.')
 p('The frontend uses TypeScript types generated from the FastAPI response schemas. Its navigation shows the pages available to the current user category, while the backend checks access again on each protected endpoint. The supplied SecureAuth project informed the layout and colour choices. The interface includes light and dark themes, locally served Geist fonts, and tables that scroll on smaller screens.')
 #4 database
 new('Relational design and normalization')
 p('The database contains the eight entities in the proposal and two supporting tables for sessions and sign-in activity. Together they contain 62 columns and 12 foreign keys. Alembic revision 0001 defines the application schema, and sql/schema.sql is generated from it. The Alembic version table tracks migrations and is not part of the application model.')
 table(['Entity group','Purpose'],[['app_user, role, permission','Current identity, responsibility category and action/resource-type vocabulary.'],['user_role, role_permission','Composite-key junction relations implementing the two many-to-many relationships.'],['resource','Stable type/key identity, owner and availability status.'],['audit_event, policy_change','Historical access outcomes and administrative change evidence.'],['login_session, security_event','Revocable server sessions and authentication investigation/throttling.']],[2.45,4.15])
 h('First normal form');p('Each role and permission occupies its own row. A user can hold several roles through USER_ROLE, rather than through a list stored inside the user record. This keeps the policy relations in first normal form and makes individual assignments easier to query.')
 h('Second normal form');p('In USER_ROLE, the combination of user_id and role_id identifies an assignment. Its assignment details describe that pair. ROLE_PERMISSION similarly uses the full role_id and permission_id pair. Role descriptions and permission attributes stay in their own tables, so they do not depend on only part of a composite key.')
 h('Third normal form');p('A role description is stored with the role, and a resource owner is stored with the resource. These attributes are not repeated in current assignment records. This separation avoids transitive dependencies in the policy model. PostgreSQL also enforces the candidate keys: user email, role name, permission action/type and resource type/key.')
 h('Historical snapshots');p('An audit event retains the email, resource key and matching role name used for that decision. For example, renaming a role later must not change the explanation of an earlier allowed request. These fields describe the event at a particular time. POLICY_CHANGE stores change details in JSONB, while the live role and permission tables remain the source for new decisions.')
 #5-7 diagrams
 for i,(title,caption) in enumerate([('Role and permission relationships','Policy model: five entities with both composite-key junctions.'),('Resources and historical records','Resource, access-decision and policy-change model; reference boxes are repeated entities.'),('Authentication support relationships','Technical session/security entities and complete foreign-key inventory.')],1):
  new(title,True);picture(QA/f'erd-{i}.png',8.4,caption)
 #8 dictionary core
 new('Data dictionary for current policy')
 p('All attributes are NOT NULL unless marked nullable in the ER diagram. Integer entity keys use PostgreSQL sequences. Timestamp columns use time zones. PK means primary key; FK means foreign key; UQ means database-enforced uniqueness.')
 for name in ['app_user','role','permission','user_role','role_permission','resource']:
  t=TABLES[name];h(name.replace('_',' ').title());parts=[]
  for c in t['columns']:
   flags=[]
   if c['pk']:flags.append('PK')
   if c['fk']:flags.append('FK '+c['fk'][0])
   if c['nullable']:flags.append('nullable')
   parts.append(c['name']+' '+('TIMESTAMPTZ' if c['type']=='DATETIME' else c['type'])+(' ['+', '.join(flags)+']' if flags else ''))
  p('; '.join(parts)+'.')
 h('Key integrity rules');p('The database rejects a second account with the same email and a second role with the same name. It also rejects duplicate permission action/type pairs and resource type/key pairs. Composite keys prevent repeated assignments, and foreign keys prevent references to missing records. CHECK constraints limit actions to READ, CREATE, UPDATE and DELETE and role categories to admin, auditor and user.')
 #9 historical dict
 new('Data dictionary for history and sessions')
 for name in ['audit_event','policy_change','login_session','security_event']:
  t=TABLES[name];h(name.replace('_',' ').title());parts=[]
  for c in t['columns']:
   flags=[]
   if c['pk']:flags.append('PK')
   if c['fk']:flags.append('FK '+c['fk'][0])
   if c['nullable']:flags.append('nullable')
   parts.append(c['name']+' '+('TIMESTAMPTZ' if c['type']=='DATETIME' else c['type'])+(' ['+', '.join(flags)+']' if flags else ''))
  p('; '.join(parts)+'.')
 h('Defaults and lifecycle');p('PostgreSQL supplies the default timestamps, and the application generates UUIDs for new events. The development seed uses earlier timestamps so that date filters can be demonstrated. Revoking a role sets its assignment to active=false. A permission mapping can be removed from the current policy, but its policy-change record remains available for investigation.')
 h('Indexes and views');p('The audit indexes support the main investigation filters: time, actor, decision and resource. Policy history has indexes on time and administrator/time; session and sign-in indexes support expiry checks and failed-login queries. The effective_user_permission view combines current active permissions, and daily_access_summary groups recorded decisions by UTC date, resource type and outcome.')
 #10 security
 new('Authentication and authorization')
 h('Authentication controls');p('Passwords are hashed with Argon2id through pwdlib. After a successful login, the browser receives a random session token in an HttpOnly cookie. PostgreSQL stores a SHA-256 digest of that token, its expiry and a CSRF token. Sessions expire after eight hours by default. Login uses a signed CSRF token and limits repeated failures. The cookie uses SameSite=Lax; an HTTPS deployment must also enable Secure. Session tokens are not stored in browser web storage.')
 h('Evaluation sequence')
 for x in ['Authenticate the actor from the server session and validate action, positive resource ID, UUID and CSRF token.','Acquire a shared policy advisory lock and the actor row lock; first check an existing request ID for a safe replay.','Check account status, resource existence and resource status before searching active assignments and active roles.','Join USER_ROLE, ROLE, ROLE_PERMISSION and PERMISSION for the requested action and resource type.','Choose the lowest matching role ID deterministically; without a match, deny by default.','Insert AUDIT_EVENT, commit durably, then return the decision. A database failure does not return ALLOWED.']:bullet(x)
 table(['Reason code','Meaning'],[['ALLOWED_BY_ROLE','An active permission mapping matched.'],['NO_MATCHING_PERMISSION','No active role grants the operation.'],['INACTIVE_ACCOUNT','An existing session belongs to a disabled account.'],['INACTIVE_RESOURCE','The registered target is disabled.'],['RESOURCE_NOT_FOUND','A valid numeric target ID is absent from the registry.']],[2.65,3.95])
 p('Invalid inputs and requests without a valid session are rejected before resource evaluation. A disabled account cannot sign in. If an account is disabled while its session still exists, an evaluation through that session records INACTIVE_ACCOUNT. An auditor can read investigation records but cannot submit evaluations or change policy.')
 #11 transaction
 new('Transactions and historical integrity')
 h('Atomic administrative changes');p('Assigning a role changes what a user can do, so the assignment and its history record must succeed together. The policy service first takes a transaction advisory lock and checks administrator authority. It validates the target records, applies the change, checks that an active administrator remains, and writes POLICY_CHANGE before committing. The same service handles revocations, permission mappings and status changes.')
 h('Rollback and concurrency');p('When the policy history insert fails, PostgreSQL rolls back the accompanying policy change. The tests check this by installing triggers that deliberately reject audit inserts. The advisory lock also serializes competing administrative updates. If two administrators try to disable their accounts, the second change is rejected when it would remove the final active administrator. A database owner can still bypass these application rules through direct SQL.')
 h('Idempotency and correlation');p('A browser may retry a request after losing a response. To avoid recording that retry as a new evaluation, AUDIT_EVENT has a unique actor_user_id/request_id pair. The same ID and payload return the existing result; a different payload with that ID is rejected. A new ID is needed to check a changed policy. The actor row lock prevents simultaneous retries from creating duplicate events.')
 h('Append only access paths');p('The application account can read and insert history, but it cannot update or delete those records or change the schema. Referenced users, roles and resources are deactivated instead of deleted. These restrictions protect history during normal application use. They do not prevent a PostgreSQL owner from changing the database directly.')
 h('Safe reporting');p('Report queries use parameters and accept only supported sort options. Tables return 20 records per page. CSV export requires both dates and permits a range of up to 93 days with no more than 5,000 matching records. The server rejects an export that exceeds either limit. Exported data excludes password hashes and session tokens, and formula-like values are escaped before opening in a spreadsheet.')
 #12 SQL
 new('SQL implementation and examples')
 p('The SQL scripts demonstrate the database concepts used by the application. They include CRUD, joins, aggregates, subqueries, views, indexes, constraints and transactions. Alembic remains the schema source; the generated standalone schema is intended for an empty database. The following examples show how permissions and access patterns can be queried.')
 h('Effective permissions through multiple joins')
 code('''SELECT DISTINCT u.email, p.action, p.resource_type
FROM app_user u
JOIN user_role ur ON ur.user_id=u.id AND ur.active
JOIN role r ON r.id=ur.role_id AND r.active
JOIN role_permission rp ON rp.role_id=r.id
JOIN permission p ON p.id=rp.permission_id
WHERE u.active
ORDER BY u.email, p.resource_type, p.action;''')
 h('Daily decisions and repeated denials')
 code('''SELECT (occurred_at AT TIME ZONE 'UTC')::date AS day,
       resource_type, decision, count(*) AS requests
FROM audit_event
GROUP BY day, resource_type, decision ORDER BY day DESC;

SELECT actor_email, count(*) AS denials
FROM audit_event
WHERE decision='DENIED'
  AND occurred_at >= now() - interval '30 days'
GROUP BY actor_email HAVING count(*) >= 3;''')
 h('Constraint and transaction demonstrations');p('The constraint demonstration attempts duplicate, orphaned and invalid-action inserts and catches the expected PostgreSQL errors. The transaction demonstration shows a committed insert, a rolled-back update and a role change rolled back together with its history record. EXPLAIN examples show the chosen execution plan. With a small seed dataset, PostgreSQL may reasonably choose a sequential scan.')
 #13 reports seed
 new('Analytical reporting and demonstration data')
 table(['Required investigation','Implementation'],[['Users and effective permissions','Five-table join and effective_user_permission view.'],['Daily allowed and denied counts by type','UTC date GROUP BY in queries.sql and daily_access_summary.'],['Policy change followed by access','Join policy subject and event actor within the following day.'],['Current roles versus historical decisions','Compare current active assignments with matching-role snapshots.'],['Repeated denied requests','GROUP BY actor with HAVING denial count threshold.'],['Changes by one administrator','Filter policy actor and assignment/revocation operations.'],['History for a selected resource','Filter immutable type/key snapshots, including report R42.']],[2.45,4.15])
 h('Synthetic seed');p('A fresh database is seeded with 10 accounts: three active administrators, three active auditors, three active ordinary users and one inactive account. There are six roles, eight permissions and 16 registered resources. The 180 decision events cover different dates and outcomes, and 13 policy records include assignments and revocations. The seed runs the authorization service to generate decisions under the same rules used by the application.')
 h('Development credentials');p('Administrator: admin@example.com. Ordinary analyst: analyst@example.com. Auditor: auditor@example.com. Shared development-only password: AccessDemo!2026#. README.md lists all nine active accounts. Never use these fixtures as production identities.')
 h('Repeatable SQL execution');code('''docker compose exec -T db psql -U dac_owner -d dac \\
  -v ON_ERROR_STOP=1 < sql/queries.sql''')
 p('The command can also run constraints.sql and transactions.sql against the demonstration database. SQL_DEMONSTRATION.md explains the purpose of each script. Query-plan costs and live counts depend on the database state, so the report does not assign fixed performance figures to these examples.')
 #14 tests
 new('Verification and actual results')
 p('The results below are from the verification run on 22 November 2026. The output files are retained with the project. Editing this submission copy on 24 November did not involve rerunning the full software suite.')
 table(['Check','Recorded result','Evidence file'],[['PostgreSQL and backend/API','113 passed; 1 upstream deprecation warning; 56.84 seconds','docs/backend-test-output.txt'],['React component/API integration','12 passed; 12.35 seconds','docs/frontend-test-output.txt'],['Playwright Chromium workflows','5 passed; 58.3 seconds','docs/browser-test-output.txt'],['Production build','TypeScript check and Vite bundle succeeded','docs/TEST_RESULTS.md'],['Clean installation and live smoke','Fresh PostgreSQL volume, migration/seed and live workflows passed','docs/TEST_RESULTS.md']],[1.85,2.4,2.35])
 h('Backend and database coverage');p('The backend tests check login, session expiry, CSRF protection and the access available to each category. They also exercise the database constraints, multiple-role decisions, revocation and historical snapshots. Separate cases test duplicate-request handling, concurrent administrator changes and rollback after a rejected audit insert. Report filters, export limits and the runtime database grants are checked as well.')
 h('Browser and UI coverage');p('Browser testing follows the three user categories through their main tasks. It covers role assignment and revocation, the resulting allowed and denied requests, audit filtering and CSV downloads. It also checks both themes and the mobile layout. The tests exposed missing select-label associations and a mobile table-header overflow; both issues were corrected before the final passing run.')
 h('Warnings and limits of evidence');p('The test run produced one Starlette warning about its httpx compatibility client. This did not cause a failure. Browser checks used Playwright with Chromium in a container. The test results and screenshots establish what was exercised in that environment; they are not an independent security audit.')
 #15 screenshots
 new('Administrator interface evidence');p('The overview brings account management, access decisions and policy history into one workspace. Its counts are read from PostgreSQL. The screenshot below shows the demonstration database during browser verification, so its values may differ from a later session.')
 picture(ROOT/'docs/screenshots/admin-dark.png',6.45,'Administrator overview in the dark theme with database-backed metrics and recent activity.')
 #16 audit screenshot
 new('Audit and decision interface evidence');picture(ROOT/'docs/screenshots/audit-filtered.png',6.65,'Auditor investigation filtered to the analyst, READ, report R42, ALLOWED and a bounded UTC date range.')
 h('Interpretation');p('The filtered table lets an auditor follow a specific actor and resource over time. Opening a row shows the stored reason, matching role and request reference. CSV uses the same filters, and the server checks the auditor role and export limits before producing a file.')
 p('The screenshots folder also contains allowed and denied decision pages, policy-change details, the light theme and mobile forms. All of the records shown are fictional development data.')
 #17 closing
 new('Demonstration setup and conclusion')
 h('Start the local system');code('''python3 scripts/configure.py
docker compose up --build -d''');p('Open http://localhost:8000 after the services start. On Windows, use python if python3 is unavailable. Docker builds the frontend, starts PostgreSQL and applies the migrations. It loads the demonstration records only when the database is empty. Keep the .env file with the database volume; a normal docker compose down stops the services without deleting the data.')
 h('Practical demonstration')
 for x in ['As the analyst, read R42 (allowed), then request DELETE on R42 (denied) and inspect personal history.','As an administrator, create/assign a report-reading role to a fictional account; show the resulting allowed request, then revoke the role and show a fresh denied request.','As an auditor, filter access history, inspect the policy change and matching-role snapshot, then export the bounded CSV.','Run the joins, aggregate reports, constraint rejection and rollback examples. Explain why the earlier allowed event remains unchanged after revocation.']:bullet(x)
 h('Limitations and future development');p('The current scope stops at application-level role permissions and investigation. MFA, SSO and self-service password recovery are not included. Backup and retention jobs also need to be arranged separately. Before use beyond a local demonstration, the deployment needs HTTPS, Secure cookies, real accounts and operational monitoring. Resource ownership could support a later policy extension, but it does not grant access in this version.')
 h('Conclusion');p('The report R42 example shows the main result: a user can be allowed to read a report and denied permission to delete it, with both outcomes retained. A later role revocation changes new decisions without rewriting the earlier result. The database supports this behaviour through separate policy and history relations, constrained mappings and transactional updates. The recorded tests cover these cases, including failures and competing administrative changes.')
 h('Submission sources and accompanying files');p('The requirements come from the Database Access Control and Audit System Proposal dated 27 September 2026. The schema and examples correspond to backend/app, Alembic revision 0001 and sql. Test output and screenshots are retained under docs. ER_Diagram.pdf contains the same three diagram views used here. Implementation references, including the SQLAlchemy documentation and the SecureAuth design reference, are listed in docs/SOURCES.md and DESIGN_REFERENCE.md.')
 path=OUT/'Project_Report.docx';doc.save(path);return path

if __name__=='__main__':
 import sys
 if '--erd' in sys.argv:print(build_erd())
 if '--report' in sys.argv:print(build_report())
