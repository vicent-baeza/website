import time
import hashlib
import os
from bs4 import BeautifulSoup
from bs4.formatter import HTMLFormatter
from list_dict import ListDict

VERSION = hashlib.sha256(str(time.time()).encode('utf-8')).hexdigest()[:32]



# -----------------
# DYNAMIC PAGE DATA
# -----------------
warnings = ListDict[str, str]()
tags = ListDict[str, str]()

# ---------------
# PAGE GENERATION
# ---------------

def path_prefix(path: str):
    parts = len(path.removeprefix('docs/').strip('/').split('/'))
    return '../' * (parts - 1)

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
    return f"""
        <header>
            <div class="content">
                <a href="{pref if pref != '' else '/'}" class="header-title">VBaeza</a>
                <div class="header-tabs unselectable">
                    <a href="{pref}work" class="highlight">
                        <i class="ri-folder-fill ri-lg"></i> Work
                    </a>
                    <a href="{pref}about" class="highlight">
                        <i class="ri-user-3-fill ri-lg"></i> About me
                    </a>
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
        if len(content) > 0 and 'class="section"' in content[-1]:
            warnings.append('Empty section')

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
        </body>
        </html>
    """

    html = BeautifulSoup(html, features="html.parser").prettify(
        formatter=HTMLFormatter(indent=4)
    )

    os.makedirs(os.path.dirname(f"docs/{path}.html"), exist_ok=True)

    with open(f"docs/{path}.html", "w", encoding="utf-8") as f:
        f.write(html)

    # dynamic data
    warnings.add(path)
    tags.add(path)


# --------
# ELEMENTS
# --------


def tag(tag_name: str, content: str | list[str], params: str = '') -> str:
    if params != '':
        params = ' ' + params
    if isinstance(content, list):
        content = ''.join(content)
    return f'<{tag_name}{params}>{content}</{tag_name}>'

def tagc(tag_name: str, classes: str, content: str | list[str] = '', params: str = '') -> str:
    if params != '':
        params = ' ' + params
    return tag(tag_name, content, f'class="{classes}"{params}')

def div(classes: str, content: str | list[str] = '', params: str = '') -> str:
    return tagc('div', classes, content, params)

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
    return tagc('a', classes, text, f'href="{href}"')

def i(classes: str):
    return tagc('i', classes)

def ul(content: list[str], classes: str = '', params: str = '', li_classes: str = '', li_params: str = ''):
    list_items = [tagc('li', li_classes, x, li_params) for x in content]
    return tagc('ul', classes, list_items, params)

def section(name: str):
    return div('section', [
        div('section-title', name),
        div('section-divider'),
    ])

def taglist(tag_names: list[str]):
    return div('tag-list', [div('tag', tag_name) for tag_name in tag_names])

def card(href: str, title: str, subtitle: str, datetext: str, date: str, content: str = '', divider: bool = True):
    return div('card btn', [
        div('card-title', title),
        div('card-dot', '•') if subtitle != '' else '',
        div('card-subtitle', subtitle) if subtitle != '' else '',
        div('card-divider' + ('' if divider else ' card-divider-hidden')),
        div('card-subtitle', datetext) if datetext != '' else '',
        div('card-dot', '•') if datetext != '' else '',
        div('card-date', date),
        div('card-content', content) if content != '' else ''
    ], f'onclick="location.href=\'{href}\';"')

def crumbs(path: str) -> str:
    parts = path.removeprefix('docs/').removesuffix('.html').strip('/').split('/')
    if len(parts) == 0:
        warnings.add(f'Invalid crumbs path "{path}"')
        return ''
    if len(parts) == 1 and parts[0] == 'index':
        return ''
    link = path_prefix(path)
    content = []
    content.append(a('index.html', 'home', 'crumb-text'))
    content.append(i('ri-arrow-right-s-line crumb-divider'))
    for part in parts[:-1]:
        link = f'{link.removesuffix('/')}/{part}'
        content.append(a(link, part, 'crumb-text'))
        content.append(i('ri-arrow-right-s-line crumb-divider'))

    content.append(div('crumb-text', parts[-1]))
    return div('crumbs', content)


BR = "<br/>"


# ----------
# MAIN PAGES
# ----------
generate("index", '', [
    h1("Vicent Baeza"),
    p("Software Engineer with a passion for math and computer science."),
    p("Currently building automation & data scrapping tools @ Facephi."),
    section('Work'),
    card('work/facephi', 'Facephi', 'AI Engineer', '', '09/2025 — Present', ul([
        'Built several automation & data scrapping tools leveraging AI agents.',
    ])),
    card('work/compliance_cms', 'Compliance CMS', 'Software Engineer', '', '07/2023 — 09/2025', ul([
        'Single-handedly developed and maintained two full-stack web applications.',
        'Planning, design, implementation & delivery of new features from scratch.',
    ])),
    section('Education'),
    card('education/master', "Master's Degree in Data Science", 'University of Alicante', '', '09/2024 — 06/2025', ul([
        'Grade: 9.05/10',
    ])),
    card('education/degree', "Degree in Computer Engineering", 'University of Alicante', '', '09/2020 — 06/2024', ul([
        'Grade: 8.81/10, including 13 honors',
        'Graduated as part of the High Academic Performance group (ARA group), with a specialization in Computing.',
        f'Received the {a('awards/extraordinary', 'Extraordinary Award in Computer Engineering')} for outstanding performance.',
    ])),
    card('education/tech_scouts', 'Tech Scouts: Computer Science', 'Harbour Space', '', '07/2019 — 07/2019', ul([
        'Intensive 3-week summer course for advanced math and computer science.',
        f'Invitation received for winning a Gold Medal in the {a('awards/oicat', 'Catalan Olympiad in Informatics')} in 2019.',
    ])),
    card('education/estalmat', 'ESTALMAT', 'Polytechnic University of Valencia', '', '07/2019 — 07/2019', ul([
        '4-year weekly math program for promoting and developing math and reasoning skills.',
        'Learned a lot of foundational concepts that fueled my current passion for math and computer science.',
    ])),
])
generate("about", 'About me', [

])


# ----
# WORK
# ----
generate("work", 'Work', [
    card('work/facephi', 'Facephi', 'AI Engineer', '', '09/2025 — Present', ul([
        'Built several automation & data scrapping tools leveraging AI agents.',
        'Extracted key information used to train production models.',
    ]) + taglist(['Python', 'LangGraph', 'MCP'])),
    card('work/compliance_cms', 'Compliance CMS', 'Software Engineer', '', '07/2023 — 09/2025', ul([
        'Single-handedly developed and maintained two full-stack web applications.',
        'Planning, design, implementation & delivery of new features from scratch.',
    ]) + taglist(['PHP', 'JS', 'Vue.JS', 'SQL', 'NLP'])),
])
generate("work/facephi", "Facephi", [

])
generate("work/compliance_cms", "Compliance CMS", [

])


# ---------
# EDUCATION
# ---------
generate("education", 'Education', [
    card('education/master', "Master's Degree in Data Science", 'University of Alicante', '', '09/2024 — 06/2025', ul([
        'Grade: 9.05/10',
    ])),
    card('education/degree', "Degree in Computer Engineering", 'University of Alicante', '', '09/2020 — 06/2024', ul([
        'Grade: 8.81/10, including 13 honors',
        'Graduated as part of the High Academic Performance group (ARA group), with a specialization in Computing.',
        f'Received the {a('awards/computer_engineering', 'Extraordinary Award in Computer Engineering')} for outstanding performance.',
    ])),
    card('education/tech_scouts', 'Tech Scouts: Computer Science', 'Harbour Space', '', '07/2019 — 07/2019', ul([
        'Intensive 3-week summer course for advanced math and computer science.',
        f'Invitation received for winning a Gold Medal in the {a('awards/oicat', 'Catalan Olympiad in Informatics')} in 2019.',
    ])),
    card('education/estalmat', 'ESTALMAT', 'Polytechnic University of Valencia', '', '09/2015 — 05/2019', ul([
        '4-year weekly math program for promoting and developing math and reasoning skills.',
        'Learned a lot of foundational concepts that fueled my current passion for math and computer science.',
    ])),
])
generate("education/master", "Master's Degree in Data Science", [

])
generate("education/degree", "Degree in Computer Engineering", [

])
generate("education/tech_scouts", "Tech Scouts: Computer Science", [

])
generate("education/estalmat", "ESTALMAT", [

])


# ------
# AWARDS
# ------
generate("awards", 'Honors & awards', [
    card('awards/computer_engineering', "Extraordinary Award in Computer Engineering", 'University of Alicante', '', '11/2024', ul([
        f'Awarded to the three students with the highest overall grades in the {a('education/degree', 'Degree in Computer Engineering')}',
    ])),
    card('awards/oicat', "Gold Medal in the 2020 Catalan Olympiad in Informatics", 'OICat', '', '09/2020'),
    card('awards/oie', "Silver Medal in the 2020 Spanish Olympiad in Informatics", 'OIE', '', '04/2020'),
    card('awards/ioi', "Participation in the 2019 International Olympiad in Informatics", 'IOI', '', '08/2019', ul([
        "Participated as part of the Spanish team",
        f"Awarded for obtaining a Gold Medal in the {a("awards/oie","Spanish Olympiad in Informatics")}"
    ])),
    card('awards/oicat', "Gold Medal in the 2019 Catalan Olympiad in Informatics", 'OICat', '', '06/2020'),
    card('awards/oie', "Gold Medal in the 2019 Spanish Olympiad in Informatics", 'OIE', '', '04/2020'),
    card('awards/oie', "Gold Medal in the 2018 Catalan Olympiad in Informatics", 'OIE', '', '06/2019'),
    card('awards/semcv', "Third Prize in the 2018 Valencian Olympiad in Mathematics", 'SEMCV', '', '05/2018'),
    card('awards/semcv', "Reached final round in the 2017 Valencian Olympiad in Mathematics", 'SEMCV', '', '05/2017'),
    card('awards/semcv', "Reached final round in the 2016 Valencian Olympiad in Mathematics", 'SEMCV', '', '05/2016'),
    card('awards/semcv', "Reached final round in the 2015 Valencian Olympiad in Mathematics", 'SEMCV', '', '05/2015'),
    card('awards/semcv', "Reached final round in the 2014 Valencian Olympiad in Mathematics", 'SEMCV', '', '05/2014'),
    card('awards/semcv', "Second Prize in the 2013 Valencian Olympiad in Mathematics", 'SEMCV', '', '06/2013'),
])
generate("awards/extraordinary", "Extraordinary Award in Computer Engineering", [

])
generate("awards/ioi", 'International Olympiad in Informatics', [

])
generate("awards/oie", 'Spanish Olympiad in Informatics', [

])
generate("awards/oicat", 'Catalan Olympiad in Informatics', [

])
generate("awards/semcv", "Valencian Community's Olympiad in Mathematics", [

])


# --------
# PROJECTS
# --------
generate("projects", 'Projects', [
    section('Professional projects'),
    card('projects/automation', "Automation & Data Scrapping Tools", 'Facephi', '', '09/2025 — Present', ul([
        'Automation & data scrapping tools leveraging AI agents.',
        'Extracted key information used to train production models.',
    ]) + taglist(['Python', 'LangGraph', 'MCP'])),
    card('projects/riskapp', "RiskApp CMS", 'Compliance CMS', '', '12/2023 — 09/2025', ul([
        'Web application to automate corporate risk assessment.',
        'Design of the entire app & complete implementation from scratch.',
    ]) + taglist(['PHP', 'JS', 'SQL'])),
    card('projects/whistleblowing', "Whistleblowing Channel", 'Compliance CMS', '', '07/2023 — 09/2025', ul([
        'Whistleblowing Channel compliant with Spanish & EU whistleblowing regulations.',
        'Planning, design, implementation & delivery of several key features.'
    ]) + taglist(['PHP', 'JS', 'Vue.JS', 'SQL', 'NLP'])),

    section('University projects'),
    card('projects/kan', "Data Science Final Project", "Master's Degree in Data Science", '', '11/2024 — 06/2025', ul([
        'Exploration and testing of the Kolmogorov-Arnold architecture for neural networks.',
    ]) + taglist(['ML', 'CNNs', 'Kolmogorov-Arnold Networks'])),
    card('projects/quantum', "Computer Engineering Final Project", "Degree in Computer Engineering", '', '09/2023 — 05/2024', ul([
        'Research project exploring the applications of Quantum Computing in ML systems.',
    ]) + taglist(['ML', 'Quantum Computing'])),
    card('projects/last_brew', "The Last Brew", 'Degree in Computer Engineering', '', '07/2023 — 09/2023', ul([
        '2D game fully programmed in Z80 Assembly for the Amstrad CPC 8-bit computer.',
        'Fluid movement, collisions, projectiles, and multiple enemy types and behaviors.',
    ]) + taglist(['Z80 Assembly', 'Amstrad CPC', 'CPCTelera'])),

    #section('Side projects'),
])
generate('projects/automation', "Automation & Data Scrapping Tools", [

])
generate('projects/riskapp', "RiskApp CMS", [

])
generate('projects/whistleblowing', "Whistleblowing Channel", [

])
generate('projects/kan', "Data Science Final Project", [

])
generate('projects/quantum', "Computer Engineering Final Project", [

])
generate('projects/last_brew', "The Last Brew", [

])


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
