# pylint: disable=C0114,C0116,C0115,C0303,W0611,R0902
import os
from datetime import date
from dataclasses import dataclass
from typing import Literal
from bs4 import BeautifulSoup
from bs4.formatter import HTMLFormatter
from dateutil.relativedelta import relativedelta
from minify_html import minify # pylint: disable=E0611
from list_dict import ListDict

VERSION = 1 #hashlib.sha256(str(time.time()).encode('utf-8')).hexdigest()[:32]


# -----
# UTILS
# -----
def is_local_path(path: str) -> bool:
    first_part = path.split('/')[0]
    return '.' not in first_part

def tryparse_date(date_str: str) -> date | None:
    if 'present' in date_str.lower():
        return date.today()
    date_parts = [x.strip() for x in date_str.strip().split('/')]
    if len(date_parts) != 2:
        warnings.append(f"Invalid date '{date_str}'")
        return None
    try:
        month = int(date_parts[0])
        year = int(date_parts[1])
        return date(year, month, 1)
    except ValueError:
        warnings.append(f"Invalid date '{date_str}'")
        return None
    
def datetext_as_datediff(two_dates: str, separator = '—') -> str:
    date_parts = [x.strip() for x in two_dates.strip().split(separator)]
    if len(date_parts) != 2:
        return ''
    date1 = tryparse_date(date_parts[0])
    date2 = tryparse_date(date_parts[1])
    if date1 is None or date2 is None:
        return ''
    d = relativedelta(date2, date1)
    if d.years == 0 and d.months == 0:
        return '1 mos'

    years = '' if d.years == 0 else ('1 yr' if d.years == 1 else f'{d.years} yrs')
    months = '' if d.months == 0 else ('1 mo' if d.months == 1 else f'{d.months} mos')
    return ' '.join([years, months])

def path_prefix(path: str):
    parts = len(path.removeprefix('docs/').strip('/').split('/'))
    return '../' * (parts - 1)

# -----------------
# DYNAMIC PAGE DATA
# -----------------
warnings = ListDict[str, str]()
tags = ListDict[str, str]()
paths = ListDict[str, str]()

def rpath(path: str) -> str:
    """Adds paths to the paths ListDict.

    Args:
        path (str): the path

    Returns:
        str: the path
    """
    paths.append(path)
    return path


# --------
# ELEMENTS
# --------
def tag(tag_name: str, content: str | list[str], params: str = '') -> str:
    if params != '':
        params = ' ' + params
    if isinstance(content, list):
        content = ''.join(content).strip()
    return f'<{tag_name}{params}>{content}</{tag_name}>'

def tagc(tag_name: str, classes: str, content: str | list[str] = '', params: str = '') -> str:
    if params != '':
        params = ' ' + params
    return tag(tag_name, content, f'class="{classes}"{params}')

def div(classes: str, content: str | list[str] = '', params: str = '') -> str:
    return tagc('div', classes, content, params)

def span(classes: str, content: str | list[str] = '', params: str = '') -> str:
    return tagc('span', classes, content, params)

def h1(text: str | list[str]):
    return tag('h1', text)

def h2(text: str | list[str]):
    return tag('h2', text)

def h3(text: str | list[str]):
    return tag('h3', text)

def p(text: str | list[str]):
    return tag('p', text)

def a(href: str, text: str | list[str], classes = ''):
    if classes != '':
        classes = f'link {classes}'
    else:
        classes = 'link'
    return tagc('a', classes, text, f'href="{rpath(href)}"')

def i(classes: str):
    return tagc('i', classes)

def b(text: str | list[str]):
    return span('bold', text)

def it(text: str | list[str]):
    """Italic"""
    return span('italic', text)

def u(text: str | list[str]):
    return tag('u', text)

def ul(content: str | list[str], classes: str = '', params: str = '', li_classes: str = '', li_params: str = ''):
    if isinstance(content, str):
        content = [content]
    list_items = [tagc('li', li_classes, x, li_params) for x in content]
    return tagc('ul', classes, list_items, params)

def img(classes: str, src: str, alt_text: str, inner_content: str | list[str] = ''):
    return tagc('img', classes, inner_content, f'src="{src}" alt="{alt_text}"')

def card_img(title: str, date_str: str, image_src: str, image_fullscreen_html_content: str | list[str]):
    return div('card cursor-pointer', [
        div('card-title', title),
        div('card-divider'),
        div('card-date', date_str),
        img('card-content', image_src, title),
        div('img-fullscreen-content', image_fullscreen_html_content),
    ])

def section(name: str):
    return div('section', [
        div('section-title', name),
        div('section-divider'),
    ])

def taglist(tag_names: list[str]):
    return div('tag-list', [div('tag', tag_name) for tag_name in tag_names])

def card(href: str, title: str, subtitle: str, datetext: str, date_str: str, content: str = '', divider: bool = True):
    if datetext == 'auto': # Automatic datetext calculation (as duration):
        datetext = datetext_as_datediff(date_str)

    return div('card btn', [
        div('card-title', title),
        div('card-dot', '•') if subtitle != '' else '',
        div('card-subtitle', subtitle) if subtitle != '' else '',
        div('card-divider' + ('' if divider else ' card-divider-hidden')),
        div('card-subtitle', datetext) if datetext != '' else '',
        div('card-dot', '•') if datetext != '' else '',
        div('card-date', date_str),
        div('card-content', content) if content != '' else ''
    ], f'onclick="location.href=\'{rpath(href)}\';"')

def crumbs(path: str) -> str:
    parts = path.removeprefix('docs/').removesuffix('.html').strip('/').split('/')
    if len(parts) == 0:
        warnings.add(f'Invalid crumbs path "{path}"')
        return ''
    if len(parts) == 1 and parts[0] == 'index':
        return ''
    link = path_prefix(path).removesuffix('/')
    content = []
    content.append(a(f'{link}/', 'home', 'crumb-text'))
    content.append(i('ri-arrow-right-s-line crumb-divider'))
    for part in parts[:-1]:
        link = f'{link}/{part}'
        content.append(a(link, part, 'crumb-text'))
        content.append(i('ri-arrow-right-s-line crumb-divider'))

    content.append(div('crumb-text', parts[-1]))
    return div('crumbs', content)


BR = "<br/>"


# ---------------
# PAGE GENERATION
# ---------------
@dataclass
class HeaderTabs():
    href: str
    name: str
    icon: str

header_tabs = [
    HeaderTabs('work', 'Work', 'ri-folder-fill'),
    HeaderTabs('projects', 'Projects', 'ri-hammer-fill'),
    HeaderTabs('education', 'Education', 'ri-graduation-cap-fill'),
    HeaderTabs('awards', 'Awards', 'ri-trophy-fill'),
    HeaderTabs('about', 'About me', 'ri-user-3-fill'),
]

def head(path: str, page_title: str = "", scripts: str = ""):
    if page_title != "":
        page_title = f"{page_title} | VBaeza"
    else:
        page_title = "VBaeza"
    pref = path_prefix(path)
    return f"""
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="{pref}styles.css?v={VERSION}">
            <link rel="stylesheet" href="{pref}fonts/remixicon/remixicon.css">
            <link rel="icon" href="{pref}images/icon-dark.png">
            <title>{page_title}</title>
            <script defer src="{pref}scripts.js?v={VERSION}"></script>
            {scripts}
        </head>
    """


def header(path) -> str:
    pref = path_prefix(path)
    tabs = '\n'.join([
        f'<a href="{pref}{rpath(tab.href)}" class="highlight"><i class="{tab.icon} ri-lg"></i> {tab.name}</a>'
        for tab in header_tabs
    ])
    return f"""
        <header>
            <div class="content">
                <a href="{pref if pref != '' else '/'}" class="header-title">VBaeza</a>
                <div class="header-tabs unselectable">
                    {tabs}
                </div>
                <div class="header-buttons">   
                    <span class="btn highlight light darkmode-button" title="Light Theme">
                        <i class="ri-sun-fill ri-lg"></i>
                    </span>
                    <span class="btn highlight dark darkmode-button" title="Dark Theme">
                        <i class="ri-moon-fill ri-lg"></i>
                    </span>
                </div>
            </div>
        </header>
    """

footer: str = """
    <footer>
        <div class="content">
            <span id='footer-text' class="footer-text">
                © 2025 Vicent Baeza
            </span>
            <div class="footer-buttons">   
                <a href="https://linkedin.com/in/vbaeza/" target="_blank" class="btn highlight" title="LinkedIn">
                    <i class="ri-linkedin-box-fill ri-lg"></i>
                </a>
                <a href="mailto:vicentbaeza7@gmail.com" target="_blank" class="btn highlight" title="Email">
                    <i class="ri-mail-fill ri-lg"></i>
                </a>
                <a href="https://github.com/vicent-baeza" target="_blank" class="btn highlight" title="GitHub">
                    <i class="ri-github-fill ri-lg"></i>
                </a>
            </div>    
        </div>                
    </footer>
"""


def generate(path: str, title: str, content: str | list[str], scripts: str = ""):    
    if isinstance(content, list):
        if len(content) > 0:
            if 'class="section"' in content[-1]:
                warnings.append('Empty section')
            if '<h1' in content[-1]:
                warnings.append('Empty <h1>')
            if '<h2' in content[-1]:
                warnings.append('Empty <h2>')
            if '<h3' in content[-1]:
                warnings.append('Empty <h3>')
        
        content = "".join(content)

    if content == '':
        warnings.append('Empty content')
        content = BR + h3('⚠️ Under construction, check back later! ⚠️')

    if title != '':
        content = h1(title) + content

    content = crumbs(path) + content

    html = f"""
        <!DOCTYPE html>
        <html lang="en">
        {head(path, title, scripts)}
        <body>
            {header(path)}
            <div class='page-content'>
                <div class="content">
                    {content}
                </div>
            </div>
            <div class="unselectable" style="color: #00000000">.</div>
            {footer}
            <div id='fullscreen'>
                <div id='fullscreen-image'>
                    <img src='images/estalmat.jpg' alt="Estalmat Certificate" class='card-content'>
                </div>
                <div id='fullscreen-card' class='card card-hl'>
                    <div id='fullscreen-card-title' class="card-title">Estalmat Participation Certificate</div>
                    <div id='fullscreen-card-date' class="card-date">05/2017</div>
                    <div id='fullscreen-card-content' class='card-content'>
                </div>
            </div>
        </body>
        </html>
    """

    html = minify(html)
    # html = BeautifulSoup(html, features="html.parser").prettify(
    #     formatter=HTMLFormatter(indent=4)
    # )

    os.makedirs(os.path.dirname(f"docs/{path}.html"), exist_ok=True)

    with open(f"docs/{path}.html", "w", encoding="utf-8") as f:
        f.write(html)

    # dynamic data
    warnings.add(path)
    tags.add(path)
    paths.add(path)


# ----------
# MAIN PAGES
# ----------
generate("index", '', [
    h1("Vicent Baeza"),
    p("Software Engineer with a passion for math and computer science."),
    p(f"Currently building automation & data scrapping tools at {a('work/facephi', 'Facephi.')}"),
])
generate("about", 'About me', [

])


# ----
# WORK
# ----
@dataclass
class Job:
    path: str
    title: str
    company: str
    date: str
    keypoints: list[str]
    tags: list[str]
    content: str | list[str]
    alt_title: str | None = None

jobs = [
    Job('work/facephi', 'AI Engineer', 'Facephi', '09/2025 — Present', [
        'Built several automation & data scrapping tools leveraging AI agents.',
        'Extracted key information used to train production models.',
    ], ['Python', 'LangGraph', 'GitHub Actions'], [

    ]),
    Job('work/compliance_cms', 'Software Engineer', 'Compliance CMS', '07/2023 — 09/2025', [
        'Single-handedly developed and maintained two full-stack web applications.',
        'Planning, design, implementation & delivery of new features from scratch.',
    ], ['PHP', 'JS', 'Vue.JS', 'SQL'], [

    ]),
    Job('work/tutoring', 'Private Tutor', 'Self-employed', '02/2021 — 06/2022', [
        'Programming and Computer Engineering lessons.',
        'Taught Algorithms, Data Structures, Memory Management, and many other programming concepts.',
    ], ['C++', 'Java', 'Python', 'MASM Assembly'], [
        p("""
            Gave Programming and Computer Engineering lessons to first, second and third year students from the University of Alicante.
            Lesson content was tailored for every student's needs, and varied greatly from student to student.
        """),
        p('Taught topics include:'),
        ul([
            f'{b('Basic programming concepts:')} If-statements, Loops, Functions, Classes, Inheritance, etc.',
            f'{b('Math:')} Binary (2s complement), Calculus, Matrix Algebra, Discrete Math and Statistics',
            f'{b('Built-in data structures:')} Vectors, Linked Lists, Sets, Dictionaries, Stacks, Queues and Priority Queues',
            f"{b('Graph algorithms:')} BFS, DFS, A* search, Dijkstra's, Kruskal's, Beam Search and Iterative Deepening",
            f'{b('Theory of computation:')} Finite-State Machines, Context-Free Grammars & Turing Machines',
            f'{b('Optimization & efficiency:')} Big-O Notation, Algorithm Analysis, Parallel Processing & Multithreading',
            f'{b('Competitive Programming:')} Dynamic Programming, Greedy Algorithms, Divide & Conquer and Branch & Cut',
            f'{b('Advanced data structures:')} Heaps, BSTs, AVL trees, Union Finds, Segment Trees, Tries and Graphs',
            f'{b('Computer Architecture:')} Memory Management, Pipelining & MASM Assembly (32-bit)',
        ], classes='text-list'),
        BR,
        p('Depending on the student, the lessons were given in C++, Java, Python, or a combination of the three.')
    ], alt_title='Private Tutoring')
]

generate('work', 'Work', [
    card(job.path, job.title, job.company, '', job.date, ul(job.keypoints) + taglist(job.tags))
    for job in jobs
])
for job in jobs:
    generate(job.path, job.alt_title or job.title, job.content)

# ---------
# EDUCATION
# ---------
@dataclass
class Education:
    path: str
    title: str
    institution: str
    date: str
    keypoints: list[str]
    content: str | list[str]

educations = [
    Education('education/master', "Master's Degree in Data Science", 'University of Alicante', '09/2024 — 06/2025', [
        'Grade: 9.05/10',
    ], [

    ]),
    Education('education/degree', 'Degree in Computer Engineering', 'University of Alicante', '09/2020 — 06/2024', [
        'Grade: 8.81/10, including 13 honors',
        'Graduated as part of the High Academic Performance group (ARA group), with a specialization in Computing.',
        f'Received the {a('awards/computer_engineering', 'Extraordinary Award in Computer Engineering')} for outstanding performance.',
    ], [

    ]),
    Education('education/tech_scouts', 'Tech Scouts: Computer Science', 'Harbour Space', '07/2019 — 07/2019', [
        'Intensive 3-week summer course focusing computer science and advanced mathematics.',
        f'Invitation received for winning a Gold Medal in the {a('awards/oicat', 'Catalan Olympiad in Informatics')} in 2019.',
    ], [
        p(f"""The Computer Science course of Tech Scouts is an intensive 3-week summer course. 
            Although the course itself can be pricey, I managed to get it for free as part of the prize for winning a Gold Medal in the {a('awards/oicat', '2019 Catalan Olympiad in Informatics')}.
        """),
        p("""
            The course, located at Harbour Space's Barcelona Campus, is tailored depending on your level (Beginner, Intermediate or Advanced). 
            A first-day exam is taken by all students in order to determine the best level for each.
            Although back then I struggled a bit in math, I managed to get the Advanced level in both computer science and math.
        """),
        p("""
            The classes themselves were extremely productive and engaging, and were exclusively taught by experts in computer science and mathematics. 
            Every class starts introducing fundamental and really interesting concepts, and then really nails them down by going trough curated problems.
            There were also many take-home problems, which were optional and would be corrected after-the-fact.
        """),
        p("""
            The things I believe were the most helpful were the advanced algorithms and data structures. 
            Before I didn't have a formal education on computer science, and was more or less self-taught.
            By the time I finished the course, I had learned a broad range of advanced data structures and algorithms, 
            which greatly helped me in future contests and really broadened my horizon in computer science.
        """),
        p("""
            Some of the things I learned thanks to the course:
        """),
        ul([
            'Binary Search Trees: AVLs, Red-black, Treaps, etc.',
            'Range Queries: Binary Index Trees, Segment Trees, Sparse Tables, etc.',
            'Union Finds (Disjoint Sets)',
            'Tries & Suffix Trees',
            'SQRT Decomposition',
            'Persistent Data Structures',
        ]),
        BR,
        p("""
            Besides all the concrete knowledge that the course provides, the most valuable aspect of it is that 
            it fundamentally changed how I aproached math and computer science problems.
            Instead of relying mostly on intuition, the approach that the course prioritized was much more formal and structured, 
            which really helped me progress and get deeper into computer science.
        """),
        p("""
            Overall, a great and memorable formative experience.
        """)
    ]),
    Education('education/estalmat', 'ESTALMAT', 'Polytechnic University of Valencia', '09/2015 — 05/2019', [
        '4-year weekly math program for promoting and developing math and reasoning skills.',
        'Learned a lot of foundational concepts that fueled my current passion for math and computer science.',
    ], [
        p("""
            ESTALMAT is a Spanish program for the promotion and development of math and reasoning skills among children and teenagers.
            Promoted by the Spanish Royal Academy of Exact, Physical and Natural Sciences, the program offers extracurricular intensive math classes.
          """),
        p(""" 
            Although the program is very exclusive (only ~25 places per year and region), it gives everyone a fair chance and is completely free.
            The first and second year the sessions are weekly; while for the third and fourth years the sessions are once every two weeks.
        """),
        p(f"""
            I managed to qualify for the Valencian Community's ESTALMAT back in 2015, after participating in the 
            {a('awards/semcv', 'Valencian Olympiad in Mathematics')}, which sparking my eventual passion for maths and computer science.
        """),
        p("""
            I remember my time at ESTALMAT very fondly. It was truly a remarkable experience, filled with amazing teachers and students alike.
        """),
        div('big-img',
            card_img(
                'ESTALMAT Participation Certificate',
                '05/2017',
                '../images/estalmat.jpg',
                [
                    BR,
                    p('Digital scan of the certificate (in Spanish).'),
                    p('English translation:'),
                    p("""The President of the Royal Academy of Exact, Physical & Natural Sciences 
                        and in their name the Coordinator of the Project ESTALMAT - Valencian Community
                        issues the following diploma for Vicent Baeza Esteve for having participated 
                        satisfactorily in the activities proposed in the Project of Detection and 
                        Stimulation of Early Mathematical Talent (ESTALMAT) during the years 2015/16 
                        and 2016/17. Valencia, 20th of May 2017
                    """)
                ],
            )
        )
    ]),
]
generate('education', 'Education', [
    card(education.path, education.title, education.institution, '', education.date, ul(education.keypoints))
    for education in educations
])
for education in educations:
    generate(education.path, education.title, education.content)


# ------
# AWARDS
# ------
@dataclass
class Awards:
    path: str
    title: str
    institution: str
    date: str
    keypoints: list[str]
    content: str | list[str]

awards = [
    Awards('awards/first_ascent', 'First Ascent Spain', 'Bending Spoons', '09/2025', [
        'Awarded to the top 20 participants in Spain',
    ], [

    ]),
    Awards('awards/computer_engineering', 'Extraordinary Award in Computer Engineering', 'University of Alicante', '11/2024', [
        f'Awarded to the three students with the highest overall grades in the {a('/education/degree', 'Degree in Computer Engineering')}',
    ], [

    ]),
    Awards('awards/ioi', 'International Olympiad in Informatics', 'IOI', '08/2019', [
        'Participated as part of the Spanish team',
        f'Awarded for obtaining a Gold Medal in the {a('/awards/oie', 'Spanish Olympiad in Informatics')}'
    ], [

    ]),
    Awards('awards/oie', 'Spanish Olympiad in Informatics', 'OIE', '2018 — 2020', [
        'Gold Medal in the 2019 edition',
        'Silver Medal in the 2018 & 2020 editions',
    ], [
        p("""
            The Spanish Olympiad in Informatics (OIE) is a yearly competition in which students from all around Spain 
            participate to test their competitive programming skills.
        """),
        p(f"""
            The olympiad is divided into two days, in which participants have to solve several problems. 
            The top 4 participants across both days classify for the {a('/awards/ioi', 'International Olympiad in Informatics')},
            in which they represent Spain in the international stage.
        """),
        p("""
            The olympiad (at least when I participated) was an online event hosted on Hackerrank,
            which was a shame, since it didn't allow participants and get to know eachother.
            I'm happy to report that the olympiad has fixed this issue since, as now the event seems to be fully on-site.
        """),
        p("""
            Although the olympiad was pretty forgettable (since it was purely online and barely lasted a couple days), 
            the study sessions building up to it were quite the experience. The olympiad back then didn't have many
            learning resources either, but thanks to it I learned many fundamental concepts, and really got to refine my
            programming and competitive programming skills.
        """),
        p(f"""
            In 2019 I managed to classify for the {a('/awards/ioi', 'International Olympiad in Informatics')}, 
            which was a really memorable experience by itself.
        """),
        BR,
         div('halfs', [
            card_img('2018 Diploma', '06/2018', '../images/oie2018.jpg', [
                BR,
                p('Digital scan of the certificate (in Spanish).'),
                p('English translation:'),
                p('The organizing committee of the'),
                p('SPANISH OLYMPIAD IN INFORMATICS'),
                p("accredits that"),
                p("Vicent Baeza"),
                p("has obtained the SILVER classification"), 
                p("in the 2018 Spanish Olympiad in Informatics"),
                p("Barcelona, 16th of June 2018")
            ]),
            card_img('2019 Diploma', '04/2019', '../images/oie2019.jpg', [
                BR,
                p('Digital scan of the certificate (in Spanish).'),
                p('English translation:'),
                p('The organizing committee of the'),
                p('SPANISH OLYMPIAD IN INFORMATICS'),
                p("accredits that"),
                p("Vicent Baeza"),
                p("has obtained the GOLD classification"), 
                p("Barcelona, 27th of June 2019")
            ]),
        ])
    ]),
    Awards('awards/oicat', 'Catalan Olympiad in Informatics', 'OICat', '2018 — 2020', [
        'Gold Medal in the 2018, 2019 & 2020 editions',
    ], [
        p("""
            The Catalan Olympiad in Informatics (OICat) is a yearly competition in which students from 
            Catalonia and the Valencian Community can participate. 
        """),
        p("""
            The olympiad features a wide range of problems, from purely logical problems to algorithmic and programming challenges.
            The programming challenges are mostly done in C++, although C, Java and Python are also accepted programming languages. 
            Some programming challenges require image processing, and those can only be done in Python.
        """),
        p(f"""
            Although the olympiad is a relatively short event (as it only lasts a single day), it is a great experience, as it allows students interested in
            competitive programming to meet eachother and build friendships and connections. 
            The organization that organizes the olympiad also provides many training and educational courses on problem solving and
            competitive programming, that can serve as learning resources and eventual preparation for the bigger {a('/awards/oie','Spanish Olympiad in Informatics')}.
        """),
        p(f"""
            Despite the short timeframe, the few times I participated were very fun and memorable. 
            I made some friends there, and it also granted me access to the {a('/education/tech_scouts', 'Harbour Space Tech Scouts')} summer course, 
            which I wouldn't have been able to attend otherwise. Overall, a very worthwhile experience!
        """),
        BR,
        div('halfs', [
            card_img('2019 Diploma', '06/2019', '../images/oicat2019.jpg', [
                BR,
                p('Digital scan of the certificate (in Catalan).'),
                p('English translation:'),
                p("Catalan Olympiad in Informatics 2019"),
                p("Certificate"),
                p("This document certifies that"),
                p("Vicent Baeza Esteve"), 
                p("has been awarded the GOLD MEDAL in the final of the 2019 Catalan Olympiad in Informatics"), 
                p("Barcelona, 15th of June 2019"),
            ]),
            card_img('2019 Gold Medal', '06/2019', '../images/oicat2019medal.jpg', [
                BR,
                p('Photo of the Gold Medal')
            ]),
            card_img('2020 Diploma', '09/2020', '../images/oicat2020.jpg', [
                BR,
                p('Digital scan of the certificate (in Catalan).'),
                p('English translation:'),
                p("Catalan Olympiad in Informatics 2020"),
                p("Certificate"),
                p("This document certifies that"),
                p("Vicent Baeza Esteve"), 
                p("has been awarded the GOLD MEDAL in the final of the 2020 Catalan Olympiad in Informatics"), 
                p("Barcelona, 5th of September 2020"),
            ]),
            card_img('2020 Gold Medal', '09/2020', '../images/oicat2020medal.jpg', [
                BR,
                p('Photo of the Gold Medal')
            ]),
        ])
    ]),
    Awards('awards/semcv', "Valencian Olympiad in Mathematics", 'SEMCV', '2013 — 2018', [
        'Third Prize in the 2018 edition',
        'Second Prize in the 2013 edition',
        'Reached final round in the 2014, 2015, 2016 & 2017 editions',
    ], [
        p("""
            Organized by the Al-Khwarizmi society, the Valencian Community's Olympiad in Mathematics (SEMCV)
            is a yearly competition in which students solve complex mathematical problems. 
            Any Valencian student in 5th or 6th grade of primary education or in secondary education can participate.
        """),
        p("""
            The competition is organized in 3 phases (Local, Provincial and Regional) and 3 levels depending on age. The Local phase is the first, and just consists of a advanced math test. 
            This is the phase that by far gets the most participation, with thousands of students enrolling each year. 
            After that, the top 30 students of each level for each province (Alacant, València and Castelló) participate in the Provincial phase, 
            and the top 8 students for each level from each province go through to the Regional phase.
        """),
        p("""
            Although the first phase is really short and simple (just a 2-hour exam), both the Provincial and Regional phases are much more drawn out,
            having many activities, several individual and team tests, lasting multiple days each.
        """),
        p("""
            This competition, despite being relatively unknown at the time, was my very first experience with extracurricular math activities, 
            and helped steered my trajectory and made me realize my passion for mathematics and, eventually, computer science. 
            I remember these competitions very fondly, not only because of the competitions themselves, 
            but also because of the many friends and colleagues that I was able to meet thanks to them.
        """),
        p("I participated from 2013 through to 2018, managing to achieve the following:"),
        ul([
            "Second Prize in the 2013 edition",
            "Third Prize in the 2018 edition",
            "Reached the Regional Phase of the competition in the 2014, 2015, 2016, and 2017 editions",
        ]),
        BR,
        div('halfs', [
            card_img('2013 Diploma', '06/2013', '../images/mat2013.jpg', [
                BR,
                p('Digital scan of the certificate (in Catalan).'),
                p('English translation:'),
                p("Olympiad in Mathematics"),
                p("Al-Khwarizmi Society for the Mathematical Education of the Valencian Community"),
                p("Diploma to Vicent Baeza Esteve for their participation in the Olympiad in Mathematics. Regional Phase"),
                p("Benidorm, 8th of June 2013"), 
                p("Provincial Coordinator"),
            ]),
            card_img('2014 Diploma', '06/2014', '../images/mat2014.jpg', [
                BR,
                p('Digital scan of the certificate (in Catalan).'),
                p('English translation:'),
                p("Olympiad in Mathematics"),
                p("The Al-Khwarizmi Society for the Mathematical Education of the Valencian Community grants the following"),
                p("Diploma"),
                p("To: VICENT BAEZA ESTEVE"),
                p("Of the school: CEIP PLA DE BARRAQUES (EL CAMPELLO)"),
                p("For their participation in the regional phase of the XXV Valencian Olympiad in Mathematics"),
                p("Xest Educational Complex, 1st of June 2014"),
                p("General Manager of the SEMCV"),
            ]),
            card_img('2016 Diploma', '05/2016', '../images/mat2016.jpg', [
                BR,
                p('Digital scan of the certificate (in Catalan).'),
                p('English translation:'),
                p("Olympiad in Mathematics"),
                p("Al-Khwarizmi Society for the Mathematical Education of the Valencian Community"),
                p("Diploma to Vicent Baeza Esteve for their participation in the Olympiad in Mathematics. Regional Phase"),
                p("Alicante, 29th of May 2016"),
                p("Provincial Coordinator"),
            ]),
            card_img('2017 Diploma', '05/2017', '../images/mat2017.jpg', [
                BR,
                p('Digital scan of the certificate (in Catalan).'),
                p('English translation:'),
                p("Olympiad in Mathematics"),
                p("The Al-Khwarizmi Society for the Mathematical Education of the Valencian Community grants the following"),
                p("DIPLOMA"),
                p("To: VICENT BAEZA ESTEVE"),
                p("Of the school: ENRIC VALOR - EL CAMPELLO"),
                p("For their participation in the Regional Phase of the XXVIII Valencian Olympiad in Mathematics"),
                p("Xest Educational Complex, 28th of March 2017"),
                p("The Provincial Coordinators"),
            ]),
            card_img('2018 Diploma', '06/2018', '../images/mat2018.jpg', [
                BR,
                p('Digital scan of the certificate (in Catalan).'),
                p('English translation:'),
                p("2018 Olympiad in Mathematics"),
                p("Regional Phase"),
                p("DIPLOMA"),
                p("On behalf of: VICENT BAEZA ESTEVE"),
                p("Al-Khwarizmi Society for the Mathematical Education of the Valencian Community (SEMCV)"),
            ]),
        ])
    ]),
]
generate('awards', 'Contests, Honors & Awards', [
    card(award.path, award.title, award.institution, '', award.date, ul(award.keypoints))
    for award in awards
])
for award in awards:
    generate(award.path, award.title, award.content)


# --------
# PROJECTS
# --------
@dataclass
class Project:
    path: str
    title: str
    institution: str
    date: str
    keypoints: str | list[str]
    tags: list[str]
    content: str | list[str]

projects = {
    'professional': [
        Project('projects/automation', 'Automation & Data Scrapping Tools', 'Facephi', '09/2025 — Present', [
            'Exploration and testing of the Kolmogorov-Arnold architecture for neural networks.',
        ], ['Python', 'LangGraph', 'GitHub Actions'], [

        ]),
        Project('projects/riskapp', 'RiskApp CMS', 'Compliance CMS', '12/2023 — 09/2025', [
            'Web application to automate corporate risk assessment.',
            'Design of the entire app & complete implementation from scratch.',
        ], ['PHP', 'JS', 'SQL'], [

        ]),
        Project('projects/whistleblowing', 'Whistleblowing Channel', 'Compliance CMS', '07/2023 — 09/2025', [
            'Whistleblowing Channel compliant with Spanish & EU whistleblowing regulations.',
            'Planning, design, implementation & delivery of several key features.'
        ], ['PHP', 'JS', 'Vue.JS', 'SQL'], [

        ]),
    ],
    'university': [
        Project('projects/kan', 'Data Science Final Project', "Master's Degree in Data Science", '11/2024 — 06/2025', [
            'Exploration and testing of the Kolmogorov-Arnold architecture for neural networks.',
        ], ['ML', 'CNNs', 'Kolmogorov-Arnold Networks'], [

        ]),
        Project('projects/quantum', 'Computer Engineering Final Project', 'Degree in Computer Engineering', '09/2023 — 05/2024', [
            'Research project exploring the applications of Quantum Computing in ML systems.',
        ], ['ML', 'Quantum Computing'], [

        ]),
        Project('projects/last_brew', "The Last Brew", 'Degree in Computer Engineering', '07/2023 — 09/2023', [
            '2D game fully programmed in Z80 Assembly for the Amstrad CPC 8-bit computer.',
            'Fluid movement, collisions, projectiles, and multiple enemy types and behaviors.',
        ], ['Z80 Assembly', 'Amstrad CPC', 'CPCTelera'], [

        ]),
    ],
    'side': [

    ]
}
projects_content = []
for project_type, project_type_projects in projects.items():
    if len(project_type_projects) == 0:
        continue
    projects_content.append(section(f'{project_type} projects'))
    for project in project_type_projects:
        projects_content.append(
            card(project.path, project.title, project.institution, '', project.date, ul(project.keypoints) + taglist(project.tags))
        )
generate('projects', 'Projects', projects_content)

for project_type, project_type_projects in projects.items():
    for project in project_type_projects:
        generate(project.path, project.title, project.content)

# -----------------
# POST-BUILD CHECKS
# -----------------
sites = list(paths.keys())
sites.append('/')
site_link_counts = {site: 0 for site in sites}
site_link_counts['/'] += 1
site_link_counts['index'] += 1
for site, site_paths in paths.items():
    for site_path in site_paths:
        path_fixed = '/' if site_path == '/' else site_path.strip('/')
        if is_local_path(path_fixed):
            if path_fixed not in sites:
                warnings[site].append(f"Invalid local path '{path_fixed}'")
            else:
                site_link_counts[path_fixed] += 1
for site, link_count in site_link_counts.items():
    if link_count == 0:
        warnings[site].append("Not linked in any other site")

# ----------------
# CONSOLE MESSAGES
# ----------------
print('Pages successfully built!')
warning_texts = []
for page, page_warnings in warnings.items():
    if len(page_warnings) > 0:
        warning_texts.append(f'⚠️  {page}: {', '.join(page_warnings)}')

if len(warning_texts) == 0:
    print('✅ No warnings')
else:
    for warning_text in warning_texts:
        print(warning_text)
