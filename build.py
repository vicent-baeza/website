# pylint: disable=C0114,C0116,C0115,C0303,W0611,R0902,W0603,C0103,C0301
import os
import hashlib
import re
import json
from datetime import date
from dataclasses import dataclass
from typing import Iterable
from dateutil.relativedelta import relativedelta
from minify_html import minify # pylint: disable=E0611
from utils import ListDict, WordScoreTrie


# -----
# UTILS
# -----

@dataclass
class SiteSection:
    title: str
    element_id: str
    content: str

SEARCH_STOPWORDS = [
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"
]

def is_external_path(path: str) -> bool:
    return path.startswith('http')

def is_file_path(path: str) -> bool:
    return path.startswith(('files', 'docs/files', '../files', '../../files'))

def is_local_path(path: str) -> bool:
    if is_external_path(path):
        return False
    first_part = path.split('/')[0]
    return '.' not in first_part

def remove_path_double_dots(path: str) -> str:
    """Converts paths like '/path', '../path' and '../../path' to 'path'"""
    path = path.removeprefix('/')
    while path.startswith('..'):
        path = path.removeprefix('..').removeprefix('/')
    return path

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

def hash_file(path: str, buffer_size : int = 65536) -> str:
    file_hash = hashlib.sha256()
    with open(path, 'rb') as file_to_hash:
        while True:
            data = file_to_hash.read(buffer_size)
            if not data:
                break
            file_hash.update(data)
    return file_hash.hexdigest()

def extract_all_ids(content: str) -> Iterable[str]:
    pattern = re.compile(r"id=(\"|')(.*?)(\1)")
    for match in re.finditer(pattern, content):
        yield match.group(2)

def extract_all_sections(content: str) -> Iterable[SiteSection]:
    content = content.replace('\n', '')
    pattern = re.compile(r"<h2(?:.*?) id=(\"|')(.*?)(\1)>(.*?)<\/h2>(.*?)(?:(?=<h2)|$)")
    for match in re.finditer(pattern, content):
        yield SiteSection(match.group(4), match.group(2), match.group(5))

def remove_html_tags(content: str) -> str:
    return re.sub(r'<.*?>', ' ', content)

CSS_HASH = 1 #hash_file('docs/styles.css')
JS_HASH = 1 #hash_file('docs/scripts.js')

# -----------------
# DYNAMIC PAGE DATA
# -----------------

# site-wide data
warnings = ListDict[str, str]()
tags = ListDict[str, str]()
paths = ListDict[str, str]()
files = ListDict[str, str]()
requested_local_paths = ListDict[str, str]()

# global data
all_local_paths = set[str](['/', ''])
search_sites = list[dict[str, str]]()
word_search_scores = dict[str, dict[int, int]]()

class Site:
    def __init__(self, path: str, title: str):
        files.add(path)
        self.path = path
        self.title = title


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

def h2(text: str | list[str], element_id: str | None = None, classes: str = '') -> str:
    params = f'id="{element_id}"' if element_id else ''
    return tagc('h2', classes, text, params)

def h2_section(title: str | list[str], element_id: str | None, content: str | list[str], margin_bottom = True) -> str:
    if isinstance(content, list):
        content = ''.join(content).strip()
    return ''.join([h2(title, element_id, '' if margin_bottom else 'no-margin-bottom'), content])

def p(text: str | list[str]):
    return tag('p', text)

def p_no_margin(text: str | list[str]):
    return tagc('p', 'no-margin', text)

def a(href: str, text: str | list[str], classes = ''):
    if classes != '':
        classes = f'link {classes}'
    else:
        classes = 'link'

    targetParam = 'target="_blank"' if is_external_path(href) or is_file_path(href) else ''
    return tagc('a', classes, text, f'href="{rpath(href)}" {targetParam}')

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

def img(classes: str, src: str, alt_text: str, inner_content: str | list[str] = '', extra_params: str = ''):
    files.append(src)
    return tagc('img', classes + ' unselectable', inner_content, f'src="{src}" alt="{alt_text}" {extra_params}')

def card_link_img(title: str, date_str: str, image_src: str, href: str, extra_classes: str = ''):
    return a(href, [
        div('card-title', title),
        div('card-divider'),
        div('card-date', date_str),
        img('card-content', image_src, title),
    ], f'card {extra_classes}')

def card_img(title: str, date_str: str, image_src: str, image_fullscreen_html_content: str | list[str], extra_classes: str = ''):
    return div(f'card cursor-pointer {extra_classes}', [
        div('card-title', title),
        div('card-divider'),
        div('card-date', date_str),
        img('card-content', image_src, title),
        div('img-fullscreen-content', image_fullscreen_html_content),
    ])

def card_img_vw(title: str, date_str: str, image_src: str, image_fullscreen_html_content: str | list[str], image_max_height_vw: int = 50):
    return div('card cursor-pointer', [
        div('card-title', title),
        div('card-divider'),
        div('card-date', date_str),
        img('card-content', image_src, title, extra_params=f'style="max-height:{image_max_height_vw}vw"'),
        div('img-fullscreen-content', image_fullscreen_html_content),
    ])

def card_img_nohover(image_src: str, image_text: str, image_alt_text: str | None = None):
    if image_alt_text is None:
        image_alt_text = image_text
    return div('card no-hover', [
        img('card-content', image_src, image_alt_text),
        div('card-center', image_text),
    ])

def card_img_nohover_vw(image_src: str, image_text: str, image_alt_text: str | None = None, image_max_height_vw: int = 50):
    if image_alt_text is None:
        image_alt_text = image_text
    return div('card no-hover', [
        img('card-content', image_src, image_alt_text, extra_params=f'style="max-height:{image_max_height_vw}vw"'),
        div('card-center', image_text),
    ])

def titlecard(image_src: str, image_alt_text: str, ul_subtitle: str, ul_text: str, dl_subtitle: str, dl_text: str, ur_subtitle: str, ur_text: str, dr_subtitle: str, dr_text: str, _tags: list[str] | None = None) -> str:
    def titlecard_block(pos: str, subtitle: str, text: str) -> str:
        return div(f'titlecard-{pos}', [div('titlecard-subtitle', subtitle), div('titlecard-text', text)])
    return div('titlecard no-margin-bottom' if _tags else 'titlecard', [
        img('', image_src, image_alt_text),
        titlecard_block('ul', ul_subtitle, ul_text),
        titlecard_block('ur', ur_subtitle, ur_text),
        titlecard_block('dl', dl_subtitle, dl_text),
        titlecard_block('dr', dr_subtitle, dr_text),
    ]) + (taglist(_tags) if _tags else '')

def job_titlecard(image_src: str, image_alt_text: str, role: str, location: str, period: str, company_website: str, _tags: list[str] | None = None):
    return titlecard(image_src, image_alt_text, 'ROLE', role, 'LOCATION', location, 'PERIOD', period, 'COMPANY WEBSITE', company_website, _tags)
def olympiad_titlecard(image_src: str, image_alt_text: str, contest: str, location: str, period: str, website: str, _tags: list[str] | None = None):
    return titlecard(image_src, image_alt_text, 'CONTEST', contest, 'LOCATION', location, 'PERIOD', period, 'WEBSITE', website, _tags) 
def education_titlecard(image_src: str, image_alt_text: str, institution: str, location: str, period: str, website: str, _tags: list[str] | None = None):
    return titlecard(image_src, image_alt_text, 'INSTITUTION', institution, 'LOCATION', location, 'PERIOD', period, 'WEBSITE', website, _tags)


def section(name: str, element_id: str = ''):
    return div('section', [
        div('section-title', name, '' if element_id == '' else f'id="{element_id}"'),
        div('section-divider'),
    ])
def title_section(title: str, elements: list[str], button_href : str | None = None, max_elements: int = 3, content_before_elements: str = ''):    
    return div('title-section', [
        div('title-section-title', title),
        div('title-section-divider'),
        div('title-section-after', a(button_href, 'View All' + i('ri-arrow-right-s-line crumb-divider'), 'no-underline')) if button_href is not None else '',
    ]) + content_before_elements + ''.join(elements[:max_elements])

def taglist(tag_names: list[str]):
    return div('tag-list', [div('tag unselectable', tag_name) for tag_name in tag_names])

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
    HeaderTabs('/career', 'Career', 'ri-folder-line'),
    HeaderTabs('/projects', 'Projects', 'ri-hammer-line'),
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
            <link rel="stylesheet" href="{pref}styles.css?v={CSS_HASH}">
            <link rel="stylesheet" href="{pref}fonts/remixicon/remixicon.css">
            <link rel="icon" href="{pref}files/icon-dark.png">
            <title>{page_title}</title>
            <script defer src="{pref}scripts.js?v={JS_HASH}"></script>
            {scripts}
        </head>
    """


def header() -> str:
    tabs = '\n'.join([
        f'<a href="{rpath(tab.href)}" class="highlight"><i class="{tab.icon} ri-lg"></i> {tab.name}</a>'
        for tab in header_tabs
    ])
    return f"""
        <header>
            <div class="content">
                <a href="/" class="header-title">VBaeza</a>
                <div class="header-tabs unselectable">
                    {tabs}
                </div>
                <div class="header-buttons">   
                    <span class="btn highlight light darkmode-button" title="Light Theme">
                        <i class="ri-sun-line ri-lg"></i>
                    </span>
                    <span class="btn highlight dark darkmode-button" title="Dark Theme">
                        <i class="ri-moon-line ri-lg"></i>
                    </span>
                    <span class="btn highlight" title="Search">
                        <i class="ri-search-line ri-lg"></i>
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

def build_word_search(content: str, site_index: int, word_value: int = 1):
    content = remove_html_tags(content).lower()

    # remove accents
    content = content.replace('á', 'a').replace('à', 'a')
    content = content.replace('é', 'e').replace('è', 'e')
    content = content.replace('í', 'i').replace('ï', 'i')
    content = content.replace('ó', 'o').replace('ò', 'o')
    content = content.replace('ú', 'u').replace('ü', 'u')
    content = content.replace('ç', 'c').replace('ñ', 'n')

    search_words = re.split(r'[^a-zA-Z]', content)
    for search_word in search_words:
        if len(search_word) <= 2 or search_word in SEARCH_STOPWORDS:
            continue
        if search_word == '':
            continue
        if search_word not in word_search_scores:
            word_search_scores[search_word] = {}
        if site_index not in word_search_scores[search_word]:
            word_search_scores[search_word][site_index] = 0
        word_search_scores[search_word][site_index] += word_value

def generate(path: str, title: str, content: str | list[str], scripts: str = "", tab_title: str | None = None):
    if isinstance(content, list):
        content = "".join(content)

    # check global content
    if content == '':
        warnings.append('Empty content')
        content = h2('⚠️ Under construction, check back later! ⚠️')
    elif 'TODO' in content:
        warnings.append('TODOs found')

    # fix path & search title
    absolute_path = path
    search_title = title
    if title == '':
        if path.removeprefix('/') in ['', 'index']:
            absolute_path = '/'
            search_title = 'Home'
    else:
        search_title = remove_html_tags(tab_title or title)

    # extract IDs & build valid paths
    site_ids = extract_all_ids(content)
    all_local_paths.add(absolute_path)
    for site_id in site_ids:
        all_local_paths.add(f'{absolute_path}#{site_id}')

    # build word search scores
    site_index = len(search_sites)
    search_sites.append({'path': absolute_path, 'title': search_title})
    build_word_search(content, site_index)
    build_word_search(title, site_index, 100)

    # build section word search scores
    all_site_sections = extract_all_sections(content)
    for site_section in all_site_sections:
        section_index = len(search_sites)
        section_path = f'{absolute_path}#{site_section.element_id}'
        section_title = f'{search_title}: {site_section.title}'
        search_sites.append({'path': section_path, 'title': section_title})
        build_word_search(content, section_index)
        build_word_search(title, section_index, 20)


    if title != '':
        content = h1(title) + content

    content = crumbs(path) + content

    html = f"""
        <!DOCTYPE html>
        <html lang="en">
        {head(path, tab_title or title, scripts)}
        <body>
            {header()}
            <div class='page-content'>
                <div class="content">
                    {content}
                </div>
            </div>
            <div class="unselectable" style="color: #00000000">.</div>
            {footer}
            <div id='fullscreen'>
                <div id='fullscreen-image'>
                    <img src='files/estalmat/diploma.jpg' alt="Estalmat Certificate" class='card-content'>
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

    with open(f"docs/{path}.html", "w", encoding="utf-8") as html_file:
        html_file.write(html)

    # reset dynamic data
    warnings.add(path)
    tags.add(path)
    paths.add(path)


# ----
# WORK
# ----
class Job(Site):
    def __init__(self, path: str, title: str, company: str, job_date: str, keypoints: list[str], job_tags: list[str], content: str | list[str], alt_title: str | None = None, alt_tab_title: str | None = None):
        super().__init__(path, title)
        self.company = company
        self.date = job_date
        self.keypoints = keypoints
        self.tags = job_tags
        self.content = content
        self.alt_title = alt_title
        self.alt_tab_title = alt_tab_title

jobs = [
    job_facephi := Job('/career/facephi', 'AI Engineer', 'Facephi', '09/2025 — Present', [
        'Built several automation & data scrapping tools leveraging AI agents.',
        'Extracted key information used to train production models.',
    ], ['Python', 'LangGraph', 'GitHub Actions'], [
        job_titlecard('../files/facephi/logo.jpg', 'Facephi Logo', 'R&D AI Engineer', 'Alicante, Spain', '09/2025 — Present', a('https://facephi.com/en/', 'facephi.com'), ['Python', 'LangGraph', 'GitHub Actions']),
        h2_section('About the company', 'about', [
            p("""
                Facephi is a biometrics company specializing in Digital Identity, Authentication & Onboarding.
                Despite being headquartered in Alicante, Spain; the company has many international clients and connections, primarily in Latin America.
            """),
            div('big-img',
                card_img_nohover(
                    '../files/facephi/office.jpg',
                    'Facephi Headquarters in Alicante, Spain',
                )
            ),
        ]),
        h2_section('My experience at the company', 'my_experience', [
            p(f"""
                My tenure at Facephi was quite short but really interesting nontheless. 
                When I joined the company in late 2025, it had well over 200 employees, making it quite the jump in size over {a('/career/compliance_cms', 'my previous employer')}, which had less than 10.
                I was also placed into R&D, one of the bigger departments of the company, which helped make this difference even more stark.
            """),
            p("""
                Because R&D is such a large department, it was further split up into subdepartments, where most tasks landed. 
                However, a small group of developers was kept to work in department-wide tasks, and as such didn't belong to any subdepartment. 
                I found myself wrangled into said small group of developers, and although it gave me greater independence and autonomy, it also made it a bit tougher at times to coordinate with other members of R&D.
            """),
        ]),
        h2_section('Automation tools', 'tools', [
            p("""
                While working at the company, most of my time  was spent building internal tools to speedup and automate tiresome, repetitive tasks.
                Most tools, despite being relatively simple in concept, required multiple integrations with the company's existing systems, which complicated the implementation quite a bit.
            """),
            p("""
                Building tools by myself in such a new environment right out of the gate was quite overwhelming. Despite this, and mostly thanks to my previous job, 
                I had quite a lot of experience managing projects entirely by myself, and once I grew accustomed to Facephi's systems the development went smoothly.
            """),
        ]),
        h2_section('Data scrapping project', 'scrapping', [
            p("""
                Another big project that I took part in was a Data Scrapping project, which was responsible for extracting suitable images for further use. 
                Although I cannot delve into the details of the project, I fully programmed the scrapper application by myself, and was completely automated.
                I also was entirely responsible for collecting all the scrapped images and delivering them to the Data R&D subdepartment for further processing, with the ultimate goal of using them to train and improve production models.
            """),
            p("""
                Although my contribution to the project ended when I delivered the final batch of images, it felt quite satisfying when, from time to time, I would see members of Data working with images that were extracted by my application.
            """),
        ]),
        h2_section('Closing thoughts', 'closing', [
            p("""

            """)
        ])
    ]),
    job_compliancecms := Job('/career/compliance_cms', 'Software Engineer', 'Compliance CMS', '07/2023 — 09/2025', [
        'Single-handedly developed and maintained two full-stack web applications.',
        'Planning, design, implementation & delivery of new features from scratch.',
    ], ['PHP', 'JS', 'Vue.JS', 'SQL'], [
        job_titlecard('../files/compliance_cms/logo.jpg', 'ComplianceCMS Logo', 'Software Engineer', 'Alicante, Spain', '07/2023 — 09/2025', a('https://compliancecms.com/', 'compliancecms.com'), ['PHP', 'JS', 'Vue.JS', 'SQL']),
        h2_section("About the company", 'about', [
            p("""
                Compliance CMS is a small Spanish consultancy firm. If offers comprehensive services in many areas of Spanish & EU law, but mainly specializes in Criminal Compliance & Corporate Risk Mitigation.
                Although the company is quite small (less than 10 employees), it manages to boast a diverse array of clients, from multinational corporations to small businesses.
            """),
            div('big-img',
                card_img_nohover(
                    '../files/compliance_cms/photo.jpg',
                    'Photo we did for a photoshoot (yes, I didn\'t have any other photos)',
                )
            ),
        ]),
        h2_section("My experience at the company", 'my_experience', [
            p(f"""
                When I first joined Compliance CMS, it was, to put it bluntly, overwhelming. 
                Not only was it my first professional job, but I was the {it('whole')} IT team, as the company's previous programmer walked out and didn't have any other developer until I came aboard.
                That meant that {it('everything')} IT-related fell on me: programming, UI & UX, databases, security..., you name it.
                To top it all off, despite it starting as a summer job, I continued working there while studying for my {a('/career/degree', 'Computer Engineering degree')}, which made it significantly more stressful and challenging.
            """),
            p("""
                Despite all that pressure, it was also extremely enriching, and I'm glad I managed to pull through. 
                Being on my own really pushed me to grow above and beyond, making me learn a lot about topics that I had barely scratched before.
                I don't know where I would be today if I hadn't had that kind of challenge early on in my professional career.
            """),
            p("""
                It's also important to add that, despite the work itself being difficult, the people people there were everything but that. Everyone was really friendy, helpful and hard-working.
            """),
        ]),
        h2_section("Whistleblowing Channel", 'whistleblowing', [
                p("""
                    The first project I tackled was fixing and improving the company's whistleblowing channel. The channel was implemented as a Vue.JS web application, with a PHP back-end that stored the data in an SQL database in a standalone server.
                    As the company was quite small, the traffic was quite limited, so this was more than enough for it to run smoothly.
                """),
                p("""
                    Most of the work that I did to improve the Whistleblowing Channel was implementing new features and general maintenance,
                    both to improve the client experience and to make it easier to manage it. It was also quite a challenge to do os while having to comply with both Spanish & EU law, as there are very stringent regulations that added tons of complexity.
                """),
                p("""
                    As the tool is closed-source, I will refrain from delving too much into specifics, but some key achievements were the following:
                """),
                ul([
                    "Automatic reminders, data blocking & data deletion in accordance with Spanish law.",
                    "Integration with a telecom service to automatically register telephone calls in the channel.",
                    "A deterministic NLP system for the automatic censoring of personal data when required by law."
                ]),
            ]),
        h2_section("RiskApp CMS", 'riskapp', [
            p(f"""
                At the time I joined, the system for doing assessing corportate risk was a confusing, unmanageable mess of an Excel sheet.
                It was remarkably difficult to make event the most minor of changes, 
                let alone check that everything is correct or to justify {it('why')} a particular risk recieved the assessment that it did.
                It was a no-brainer to try to put the system in a web application, in a similar manner to the whistleblowing channel, 
                so as to greatly improve expandability, testability, audit capability, and to automate the most tedious and repetitive parts of the risk assessment process.
            """),
            p("""
                The planning, design, implementation, delivery & maintainance of this application, which eventually became known as the RiskApp CMS, fell completely on my hands.
                It  was almost-completely built using solely PHP. 
                As it needed to be robust, performant, and be able to handle complex business logic, I decided to develop a simple-yet-effective interface, that refreshed completely everytime but didn't need to depend on complex javascript frameworks or other big dependencies.
            """),
            p("""
                As a result, altough I needed to put in a bit of extra legwork at the beginning, the resulting application was really easy to expand, maintain, and understand.
                With a bit of clever performance optimizations, it was also extremely performant, despite the complex computations and cross-referenceing of data that it needed to do.
            """),
            p("""
                The only real limitation of this approach was that the interface, while extremely functional and responsive, was quite basic, with mostly static components that completely refreshed the page every time you wanted to switch.
                Still, I'm really proud of what I managed to build in two short years, completely from scratch no less!
            """),
            p("""
                As with the whistleblowing channel, I can't go into the nitty-gritty of the application, as it is also closed-source. However, here are some key features of it:
            """),
            ul([
                "All risk assessments generate a human-readable explanation of the calculation, to check that the system is working as intended.",
                "Automatic storage and display of previous assessments, having a sorted history of every previously calculated risk.",
                "Integrated audit capabilities that record in real time all changes that might affect risk calculation.",
            ]),
        ]),
        h2_section("Closing thoughts", 'closing', [
            p("""
                I remember my time at Compliance CMS really fondly. Although the work was quite overwhelming at times, it made me grow and greatly helped me refine my skills.
                The challenge of being the only developer in the whole company made me learn about many topics, further enriching my tenure at the company, and made me become the generalist I am today.
            """),
        ]),
    ]),
    job_tutoring := Job('/career/tutoring', 'Private Tutor', 'Self-employed', '02/2021 — 06/2022', [
        'Programming and Computer Engineering lessons.',
        'Taught Algorithms, Data Structures, Memory Management, and many other programming concepts.',
    ], ['C++', 'Java', 'Python', 'MASM Assembly'], [
        p("""
            Gave Programming and Computer Engineering lessons to first, second and third year students from the University of Alicante.
            Lesson content was tailored to every student's needs, and varied greatly from student to student.
        """),
        p('Taught topics include:'),
        ul([
            f'{b('Basic Programming Concepts:')} If-statements, Loops, Functions, Classes, Inheritance, etc.',
            f'{b('Math:')} Binary (2s complement), Calculus, Matrix Algebra, Discrete Math and Statistics',
            f'{b('Basic Data Structures:')} Vectors, Linked Lists, Sets, Dictionaries, Stacks, Queues and Priority Queues',
            f"{b('Graph Algorithms:')} BFS, DFS, A* search, Dijkstra's, Kruskal's, Beam Search and Iterative Deepening",
            f'{b('Theory of computation:')} Finite-State Machines, Context-Free Grammars and Turing Machines',
            f'{b('Optimization & Efficiency:')} Big-O Notation, Algorithm Analysis, Parallel Processing and Multithreading',
            f'{b('Competitive Programming:')} Dynamic Programming, Greedy Algorithms, Divide & Conquer and Branch & Cut',
            f'{b('Advanced Data Structures:')} Heaps, BSTs, AVL trees, Union Finds, Segment Trees, Tries and Graphs',
            f'{b('Computer Architecture:')} Memory Management, Pipelining and MASM Assembly (32-bit)',
        ], classes='text-list'),
        BR,
        p('Depending on the student, the lessons were given in C++, Java, Python, or a combination of the three.')
    ], alt_title='Private Tutor' + taglist(['C++', 'Java', 'Python', 'MASM Assembly']), alt_tab_title='Private Tutor')
]

for job in jobs:
    generate(job.path, job.alt_title or job.company, job.content, tab_title=job.alt_tab_title or job.alt_title or job.company)


# ---------
# EDUCATION
# ---------
class Education(Site):
    def __init__(self, path: str, title: str, institution: str, _date: str, keypoints: list[str], content: str | list[str]):
        super().__init__(path, title)
        self.institution = institution
        self.date = _date
        self.keypoints = keypoints
        self.content = content

educations = [
    education_master := Education('/career/master', "Master's Degree in Data Science", 'University of Alicante', '09/2024 — 06/2025', [
        'Grade: 9.05/10',
    ], [
        education_titlecard('../files/uni/logo.jpg', 'University of Alicante Logo', 'University of Alicante', 'Alicante, Spain', '09/2024 — 06/2025', a('https://web.ua.es/en/masteres/ciencia-de-datos/', 'web.ua.es/masteres/ciencia-de-datos')),
        h2_section("About the degree", 'about', [
            p("""
                The Data Science Master's Degree of the University of Alicante, as the name implies, is a master's degree that delves deep in Data Science and Machine Learning,
                refining and expanding skills learned from related undergraduate degrees.
                The master is only 1-year long, and it taught fully on-site.
            """),
            p_no_margin(f"""
                On the 2024 to 2025 school year, almost all classes were taught in the {a('https://maps.app.goo.gl/vjyehHTWuDvQpepY6', 'Faculty of Science #6')}, affectionately called The Bunker for its distinctive, harsh concrete facade.  
            """), 
            div('big-img',
                card_img_nohover_vw(
                    '../files/uni/master/ciencias6.jpg',
                    "Faculty of Science #6 aka 'The Bunker', University of Alicante",
                )
            ),
            p("""
                The master's degree delves deep into many Data Science topics, including: 
            """),
            ul([
                'Math & Statistics',
                'Data Modeling',
                'Data Mining & Data Scrapping',
                'Data Processing and Cleaning',
                'Data Visualization and Plotting',
                'Machine Learning, including CNN, RNN & Transformer architectures',
            ]),
            BR,
            p(f"""
                The whole curriculum, including compulsory and optional subjects, can be seen in the {a('https://web.ua.es/en/masteres/ciencia-de-datos/curriculum.html', "official site for the master's degree")}.
            """),
        ]),
        h2_section('My experience', 'my_experience', [
            p("""
                I managed to achieve an average grade of 9.05/10, and completed the entire master's degree in the educational year of 2024 to 2025.
            """),
            div('big-img',
                card_img_nohover_vw(
                    '../files/uni/master/graduation.jpg',
                    f"Receiving the diploma alongside four other fellow graduates. {a('https://audiovisual.ua.es/fotoweb/archives/5014-2025-Universidad-de-Alicante/?25=TURNO%202', 'Source')}",
                    "Receiving the diploma alongside four other fellow graduates.",
                )
            ),
            p(f"""
                Altough the master's delved quite deep in many areas of Data Science and Machine Learning,
                some lessons overlapped with the Computation specialization of the {a('/career/degree', 'University Degree in Computing Engineering')}, which I had already completed, so it was a bit of a shame to be re-taught some lessons.
            """),
            div('halfs limit-height', [
                card_img('Diploma', '11/2025', '../files/uni/master/diploma.jpg', [
                    BR,
                    p('Digital scan of the certificate (in Spanish).'),
                    p('English translation:'),
                    p('University of Alicante'),
                    p('Polytechnic School'),
                    p("AWARDS THIS"),
                    p("DIPLOMA"),
                    p("to"), 
                    p("Baeza Esteve, Vicent"),
                    p("University Master's Degree in Data Science"),
                    p("Alicante, 21st of November 2025"),
                ]),
            ]),
        ]),
        h2_section('Final project', 'final_project', [
            p("""
                The Master's Degree in Data Science requires a final project as part of its graduation requirements, which must be done individually for every student and defended in front of a tribunal of professors.
            """),
            p("""
                My final project, titled "Exploration of architectures based on Kolmogorov-Arnold Networks", explores and tests the Kolmogorov-Arnold architecture for neural networks, 
                which was at the time a promising alternative to traditional MLPs.
            """),
            p("""
                The complete report (in Spanish) can be seen below:
            """),
            div('big-img limit-height',
                card_link_img(
                    'Data Science Final Project Report',
                    '06/2025',
                    '../files/uni/master/tfm_portada.jpg',
                    '../files/uni/master/tfm.pdf'
                )
            ),
        ]),
    ]),
    education_degree := Education('/career/degree', 'Degree in Computer Engineering', 'University of Alicante', '09/2020 — 06/2024', [
        'Grade: 8.81/10, including 13 honors',
        'Graduated as part of the High Academic Performance group (ARA group), with a specialization in Computing.',
        f'Received the {a('/career/computer_engineering', 'Extraordinary Award in Computer Engineering')} for outstanding performance.',
    ], [
        education_titlecard('../files/uni/logo.jpg', 'University of Alicante Logo', 'University of Alicante', 'Alicante, Spain', '09/2020 — 06/2024', a('https://web.ua.es/en/grados/grado-en-ingenieria-informatica/', 'web.ua.es/en/grados/grado-en-ingenieria-informatica')),
        h2_section("About the degree", 'about', [
            p("""
                The Computer Engineering Degree of the University of Alicante is one of the biggest degrees of the university, 
                as it provides comprehensive, well-rounded education in everything related to computers and information systems.
                The 4-year degree is taught in buildings all around the university campus, and is fully on-site. 
            """),
            p_no_margin("""
                Most theoretical classes were given in the General Lecture Buildings #2 & #3, while most practical lessons were given in the many Polytechnic University Colleges scattered throughout the campus.
            """),
            div('halfs', [
                card_img_nohover_vw(
                    '../files/uni/degree/aulario2.jpg',
                    f'{a('https://maps.app.goo.gl/Qcc5nMVLtiynigZd7', 'General Lecture Building #2')}, University of Alicante',
                    'General Lecture Building #2, University of Alicante',
                ),
                card_img_nohover_vw(
                    '../files/uni/degree/politecnica1.jpg',
                    f'{a('https://maps.app.goo.gl/NNCaDZYuusAsSt4c9', 'Polytechnic University College #1')}, University of Alicante',
                    'Polytechnic University College #1, University of Alicante',
                ),
            ]),
            p("""
                The degree teaches a bit of everything in the first three years, including:
            """),
            ul([
                "Mathematics & Theoretical Frameworks of Computation",
                "Statistics & Data Analysis",
                "Programming, from low-level Assembly & C++ to high-level Java and Python",
                "Operating System Configuraton & Programming",
                "Multithreading & GPU programming (CUDA)",
                "Software Development & Software Design, including SOLID & other principles",
                "Algorithm Analysis & Data Structures",
                "Computer & Hardware Architecture & Design",
            ]),
            BR,
            p("""
                After the third year, every student gets to choose their specialization, which determines almost all subjects for the fourth year and one for the third. 
                Each one focuses on certain areas of computer engineering:
            """),
            ul([
                f"{b('Software Engineering')}: Application development, Web development and Software Design",
                f"{b('Computer Engineering')}: Embedded & Real-Time Systems, Robotics and Computer Hardware",
                f"{b('Computation')}: Machine Learning, Data Analysis, Theory of Computation and Data Science",
                f"{b('Information Systems')}: Business Administration and Process Management",
                f"{b('Information Technology')}: Computer Networks, Cloud Computing and Cybersecurity",
            ]),
            BR,
            p(f"""
                The whole curriculum, including all specializations and subjects, can be seen in the {a('https://web.ua.es/en/grados/grado-en-ingenieria-informatica/curriculum.html#Plan-1', 'official site for the degree')}.
            """),
        ]),
        h2_section("My experience", 'my_experience', [
            p(f"""
                Although some courses were difficult & stressful at times, almost all were extremely fruitful and worthwhile. 
                While I had {it('some')} computer & programming know-how before, the degree expanded & refined existing skills, while providing lots of new resources and learning opportunities. 
            """),
            p("""
                I chose to specialize in Computing, which delved deep in Algorithms, Data Structures, Math & Data Analysis; and also introduced Machine Learning, Computer Vision & Compiler Programming.
                I also took a couple courses on Networking & Cloud Computing from the Computer Networks specialization.
            """),
            div('big-img',
                card_img_nohover(
                    '../files/uni/degree/graduation.jpg',
                    f'Receiving the graduation diploma alongside both other honorees of the 2024 Extraordinary Award in Computer Engineering. {a('https://eps.ua.es/es/graduacion/graduacion-2024.html', 'Source')}',
                    'Honorees of the 2024 Extraordinary Award in Computer Engineering',
                ),
            ),
            p(f"""
                I managed to achieve an average grade of 8.81/10, which was the 2nd highest among the 113 graduates in 2024.
                Such a feat awarded me the {a('/career/computer_engineering', 'Extraordinary Award in Computer Engineering')}.
                I also recieved honors in 13 out of the 38 courses of the degree, which (to my knowledge) was the hightest number out of anyone that graduated in 2024.
            """),
            div('halfs limit-height', [
                card_img('Diploma', '11/2024', '../files/uni/degree/diploma.jpg', [
                    BR,
                    p('Digital scan of the certificate (in Spanish).'),
                    p('English translation:'),
                    p('University of Alicante'),
                    p('Polytechnic School'),
                    p("AWARDS THIS"),
                    p("DIPLOMA"),
                    p("to"), 
                    p("Baeza Esteve, Vicent"),
                    p("Degree in Computer Engineering — 2010 Plan"),
                    p("Alicante, 22nd of November 2024"),
                ]),
                card_img('Official Certificate', '06/2024', '../files/uni/degree/title.jpg', [
                    BR,
                    p('Digital scan of the certificate (in Spanish).'),
                    p('Some personal details have been redacted.'),
                    p('English translation:'),
                    p('Philip the VI, King of Spain'),
                    p('and in his name the'),
                    p("President of the University of Alicante"),
                    p("In accordance with the provisions and circumstances provided for by the current legislation"),
                    p("Vicent Baeza Esteve"), 
                    p("Born on [...] in El Campello (Alicante)"),
                    p('of Spanish nationality'),
                    p('has finished in June 2024, the official university studies'),
                    p('conducent to the official university TITLE of'),
                    p('GRADUATE in Computer Engineering by the University of Alicante'),
                    p('pursuant to the Council of Ministers Agreement of the 17th of June 2011,'),
                    p('this official certificate is issued with validity whithin the whole national territory'),
                    p('which entitles the recipient to enjoy the rights'),
                    p('that this certificate grants in accordance to current provisions'),
                    p('Given in Alicante, 21st of June, 2024'),
                ]),
            ]),
        ]),
        h2_section("Final Project", 'final_project', [
            p("""
                The Computer Engineering Degree, like many other university degrees, requires a lengthy final project as part of its graduation requirements.
            """),
            p("""
                My final project, titled "Quantum Computing and its applications in Artificial Intelligence", 
                was an exploratory project centered in the possible applications of Quantum Computing for speeding up and enhancing Machine Learning systems. 
            """),
            p("""
                The complete report (in Spanish) can be seen below:
            """),
            div('big-img limit-height',
                card_link_img(
                    'Computer Engineering Final Project Report',
                    '05/2024',
                    '../files/uni/degree/tfg_portada.jpg',
                    '../files/uni/degree/tfg.pdf'
                )
            ),
        ]),
    ]),
    education_techscouts := Education('/career/tech_scouts', 'Tech Scouts: Computer Science', 'Harbour Space', '07/2019 — 07/2019', [
        'Intensive 3-week summer course focusing computer science and advanced mathematics.',
        f'Invitation received for winning a Gold Medal at the {a('/career/oicat', 'Catalan Olympiad in Informatics')} in 2019.',
    ], [
        education_titlecard('../files/techScouts/logo.jpg', 'Harbour Space Logo', 'Harbour Space', 'Barcelona, Spain', '07/2019', a('https://harbour.space/', 'harbour.space')),
        p(f"""The Computer Science course of Tech Scouts is an intensive 3-week summer course. 
            Although the course itself can be pricey, I managed to get it for free as part of the prize for winning a Gold Medal at the {a('/career/oicat', '2019 Catalan Olympiad in Informatics')}.
        """),
        p_no_margin("""
            The course, which was hosted in the St. Paul's School Campus in Barcelona, is tailored depending on your level (Beginner, Intermediate or Advanced). 
            A first-day exam is taken by all students in order to determine the best level for each.
            Although back then I struggled a bit in math, I managed to get the Advanced level in both computer science and math.
        """),
        div('big-img',
            card_img_nohover(
                '../files/techScouts/campus.jpg',
                f'St Paul\'s School Campus, Barcelona. {a('https://www.stpauls.es/ca/', 'Source')}',
                'St Paul\'s School Campus, Barcelona',
            )
        ),
        p_no_margin("""
            The classes themselves were extremely productive and engaging, and were exclusively taught by experts in computer science and mathematics. 
            Every class starts introducing fundamental concepts, and then thoroughly nails them down by going trough curated problems one by one.
            There were also many take-home problems, which were optional and would be corrected after-the-fact.
        """),
        div('big-img',
            card_img_nohover(
                '../files/techScouts/inauguration.jpg',
                f'Tech Scouts 2019 inauguration. {a('https://www.youtube.com/watch?v=ubKpdt0o-Vc', 'Source')}',
                'Tech Scouts 2019 inauguration',
            )
        ),
        p("""
            The things I believe were the most helpful were the advanced algorithms and data structures. 
            Before I didn't have a formal education on computer science, and was more or less self-taught.
            By the time I finished the course, however, I had learned a broad range of advanced data structures and algorithms, 
            which greatly benefited me in future contests and helped broaden my horizon when studying computer science.
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
    education_estalmat := Education('/career/estalmat', 'ESTALMAT', 'Polytechnic University of Valencia', '09/2015 — 05/2019', [
        '4-year weekly math program for promoting and developing math and reasoning skills.',
        'Learned a lot of foundational concepts that fueled my current passion for math and computer science.',
    ], [
        education_titlecard('../files/estalmat/logo.jpg', 'ESTALMAT CV Logo', 'Estalmat Comunitat Valenciana', 'Alicante, Valencia & Castellón', '09/2015 — 05/2019', a('https://estalmatcv.blogs.uv.es/', 'estalmatcv.blogs.uv.es')),
        p("""
            ESTALMAT is a Spanish program for the promotion and development of math and reasoning skills among children and teenagers.
            Promoted by the Spanish Royal Academy of Exact, Physical and Natural Sciences, the program offers extracurricular intensive math classes.
          """),
        p(""" 
            Although the program is very exclusive (only ~25 places per year and region), it gives everyone a fair chance and is completely free.
            The first and second year the sessions are weekly; while for the third and fourth years the sessions are once every two weeks.
        """),
        p_no_margin(f"""
            I managed to qualify for the Valencian Community's ESTALMAT back in 2015, after participating in the 
            {a('/career/semcv', 'Valencian Olympiad in Mathematics')}, which sparked my eventual passion for maths and computer science.
        """),
        div('big-img',
            card_img_nohover(
                '../files/estalmat/reunion.jpg',
                f'Some members of ESTALMAT 2015-2019, reunited. {a('https://semcv.org/faseautonomica/olimpiades-autonomiques-anteriors/988-xxix-olimpiada-matematica-2018', 'Source')}',
                'ESTALMAT 2015-2019 reunion.',
            )
        ),
        p("""
            I remember my time at ESTALMAT very fondly. It was truly a remarkable experience, filled with amazing teachers and students alike.
        """),
        div('big-img',
            card_img(
                'ESTALMAT Participation Certificate',
                '05/2017',
                '../files/estalmat/diploma.jpg',
                [
                    BR,
                    p('Digital scan of the certificate (in Spanish).'),
                    p('English translation:'),
                    p("""
                        The President of the Royal Academy of Exact, Physical & Natural Sciences 
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
for education in educations:
    generate(education.path, education.title, education.content)


# ------
# AWARDS
# ------
class Awards(Site):
    def __init__(self, path: str, title: str, institution: str, _date: str, keypoints: list[str], content: str | list[str]):
        super().__init__(path, title)
        self.institution = institution
        self.date = _date
        self.keypoints = keypoints
        self.content = content

awards = [
    award_first_ascent := Awards('/career/first_ascent', 'First Ascent Spain', 'Bending Spoons', '09/2025', [
        'Awarded to the top 20 participants in Spain',
    ], [

    ]),
    award_computer_engineering := Awards('/career/computer_engineering', 'Extraordinary Award in Computer Engineering', 'University of Alicante', '11/2024', [
        f'Awarded to the three students with the highest overall grades in the {a('/career/degree', 'Degree in Computer Engineering')}',
    ], [
        olympiad_titlecard('../files/uni/logo.jpg', 'University of Alicante Logo', 'University of Alicante Extraordinary Award', 'Alicante, Spain', '2024', a('https://www.ua.es/en/', 'ua.es')),
        p(f"""
            The Extraordinary Award ({it('Premio Extraordinario')} in Spanish) is a prestigious award given by the University of Alicante to the
            students that graduated with the highest overall grades for that school year. The award demostrates outstanding performance and commitment to academic excellence.
        """),
        p_no_margin(f"""
            There is a separate award for each bachelor's and master's degree offered by the university.
            For each degree, one award is given for every 50 students that graduated that year. 
            In the case of the {a('/career/degree', 'Degree in Computer Engineering')}, 3 awards were given in 2024, as more that 100 students graduated that year.
        """),
        div('big-img',
            card_img_nohover(
                '../files/uni/degree/graduation.jpg',
                f'Honorees of the 2024 Extraordinary Award in Computer Engineering. {a('https://eps.ua.es/es/graduacion/graduacion-2024.html', 'Source')}',
                'Honorees of the 2024 Extraordinary Award in Computer Engineering',
            )
        ),
        p("""
            I managed to get the 2nd award, with an average grade over the whole degree of 8.81/10. 
            The other awarded students were Eric Ayllón Palazón and Diego Luchmun Corbalán, also pictured in the above photo.
        """),
        div('big-img',
            card_img_vw('Certificate for the Extraordinary Award', '01/2025', '../files/uni/degree/award.jpg', [
                BR,
                p('Digital scan of the certificate (in Spanish & Catalan)'),
                p('Some personal details have been redacted.'),
                p('English translation:'),
                p('University of Alicante'),
                p('Amparo Navarro Faure'),
                p('President of the University of Alicante'),
                p('I certify:'),
                p('That Vicent Baeza Esteve'),
                p('born on the day [REDACTED] in El Campello'),
                p('province of Alicante, with Spanish nationality'),
                p('with national identity number (or passport) [REDACTED]'),
                p('has obtained, in this university, as of November 29th, 2024'),
                p('the extraordinary award in Computer Engineering '),
                p('Whereupon to all extent and consequence, I hereby issue this certificate, in Alicante, January 28th 2025'),
            ], 50),
        ),
    ]),
    award_ioi := Awards('/career/ioi', 'International Olympiad in Informatics', 'IOI', '08/2019', [
        'Participated as part of the Spanish team',
        f'Awarded for obtaining a Gold Medal in the {a('/career/oie', 'Spanish Olympiad in Informatics')}'
    ], [
        olympiad_titlecard('../files/ioi/logo.jpg', 'IOI Logo', 'International Olympiad in Informatics', 'Baku, Azerbaijan', '2019', a('https://ioinformatics.org', 'ioinformatics.org')),
        p("""
            The International Olympiad in Informatics (IOI) is a yearly competition in which students from all around the world 
            test their competitive programming skills. It is one of the most prestigious competitions in the world of competitive programming, and to participate you have to get selected through your country's olympiad process.
        """),
        p(f"""
            In Spain, in order to participate in the IOI you have to win a Gold Medal at the {a('/career/oie', 'Spanish Olympiad in Informatics')}. 
            Despite my somewhat lackluster knowledge of algorithms and data structures at the time, I managed to win a Gold Medal in 2019 and got to participate in the IOI as part of the Spanish team.
        """),
        p_no_margin("""
            The 2019 IOI was hosted in Baku, Azerbaijan. The whole event lasted a whole week, and was composed of many experiences and events around the city, where we could meet other participants and mingle. 
            Of course, there also was quite a bit of problem-solving, compressed into two 5-hour sessions hosted at the Baku National Gymnastics Arena.
        """),
        div('big-img',
            card_img_nohover(
                '../files/ioi/stadium.jpg',
                f'National Gymnastics Arena in Baku, Azerbaijan. {a('https://olimpiada-informatica.org/content/resultados-ioi-2019-en-bak%C3%BA-azerbaiy%C3%A1n', 'Source')}',
                'National Gymnastics Arena in Baku, Azerbaijan',
            )
        ),
        p_no_margin("""
            During the whole week, we were housed in the Athlete's Village, a very large aparment complex completely booked for the IOI.
        """),
        div('big-img',
            card_img_nohover(
                '../files/ioi/village.jpg',
                f'Athletes\' Village in Baku, Azerbaijan. {a('https://bakuathletesvillage.com/', 'Source')}',
                'Athletes\' Village in Baku, Azerbaijan',
            )
        ),
        p("""
            Although I did not perform very well, primarily due to my aforementioned weak problem-solving skills at the time, it was a very enriching and memorable experience.
            Even after all these years, I vividly remember certain parts of the experience, 
            such a game of Giant Tetris being played in the hall of the Village, 
            the Japanese team trying to hand out stapleless staplers to every participant, 
            or playing One Night Ultimate Werewolf at the airport at midnight with the Swiss team while waiting to catch our return flight.
            A great time indeed.
        """),
        div('big-img',
            card_img_vw(
                'IOI Participation Certificate',
                '08/2019',
                '../files/ioi/diploma.jpg',
                [
                    BR,
                    p('Digital scan of the certificate.')
                ],
                50
            )
        )
    ]),
    award_oie := Awards('/career/oie', 'Spanish Olympiad in Informatics', 'OIE', '2018 — 2020', [
        'Gold Medal in the 2019 edition',
        'Silver Medal in the 2018 & 2020 editions',
    ], [
        olympiad_titlecard('../files/oie/logo.jpg', 'OIE Logo', 'Spanish Olympiad in Informatics', 'Barcelona, Spain', '2018 — 2020', a('https://olimpiada-informatica.org', 'olimpiada-informatica.org')),
        p("""
            The Spanish Olympiad in Informatics (OIE) is a yearly competition in which students from all around Spain 
            participate to test their competitive programming skills.
        """),
        p(f"""
            The olympiad is divided into two days, in which participants have to solve several problems. 
            The top 4 participants across both days classify for the {a('/career/ioi', 'International Olympiad in Informatics')},
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
            In 2019 I managed to classify for the {a('/career/ioi', 'International Olympiad in Informatics')}, 
            which was a really memorable experience by itself.
        """),
        BR,
        div('halfs limit-height', [
            card_img('2018 Diploma', '06/2018', '../files/oie/diploma2018.jpg', [
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
            card_img('2019 Diploma', '04/2019', '../files/oie/diploma2019.jpg', [
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
        ]),
    ]),
    award_oicat := Awards('/career/oicat', 'Catalan Olympiad in Informatics', 'OICat', '2019 — 2020', [
        'Gold Medal in the 2019 & 2020 editions',
    ], [
        olympiad_titlecard('../files/oicat/logo.jpg', 'OICat Logo', 'Catalan Olympiad in Informatics', 'Barcelona, Spain', '2019 — 2020', a('https://olimpiada-informatica.cat', 'olimpiada-informatica.cat')),
        p("""
            The Catalan Olympiad in Informatics (OICat) is a yearly competition in which students from 
            Catalonia and the Valencian Community can participate. 
        """),
        p_no_margin("""
            The olympiad features a wide range of problems, from purely logical problems to algorithmic and programming challenges.
            The programming challenges are mostly done in C++, although C, Java and Python are also accepted programming languages. 
            Some challenges require image processing, and those can only be done in Python.
        """),
        div('big-img',
            card_img_nohover(
                '../files/oicat/photo2019.jpg',
                f'Participants (including me!) solving problems in the 2019 OICat. {a('https://olimpiada-informatica.cat/oicat-2019/', 'Source')}',
                'OICat participants solving problems',
            )
        ),
        p(f"""
            Although the olympiad is a relatively short event (as it only lasts a single day), it is a great experience, as it allows students interested in
            competitive programming to meet eachother and build friendships and connections. 
            The organization that organizes the olympiad also provides many training and educational courses on problem solving and
            competitive programming, that can serve as learning resources and eventual preparation for the bigger {a('/career/oie','Spanish Olympiad in Informatics')}.
        """),
        p_no_margin("""
            I managed to get a Gold Medal (the hightest prize possible) in the 2019 and the 2020 editions of the olympiad: 
        """),
        div('halfs', [
            card_img_nohover_vw(
                '../files/oicat/winners2019.jpg',
                f'2019 OICat winners. {a('https://olimpiada-informatica.cat/oicat-2019/', 'Source')}',
                '2019 OICat winners',
            ),
            card_img_nohover_vw(
                '../files/oicat/winners2020.jpg',
                f'2020 OICat winners. {a('https://olimpiada-informatica.cat/oicat-2020/', 'Source')}',
                '2020 OICat winners',
            )
        ]),
        p(f"""
            Despite the short timeframe, both times I participated were very fun and memorable. 
            I made some friends there, and it also granted me access to the 2019 {a('/career/tech_scouts', 'Harbour Space Tech Scouts')} summer course, 
            which I wouldn't have been able to attend otherwise. Overall, a very worthwhile experience!
        """),
        BR,
        div('halfs limit-height', [
            card_img('2019 Diploma', '06/2019', '../files/oicat/diploma2019.jpg', [
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
            card_img('2019 Gold Medal', '06/2019', '../files/oicat/medal2019.jpg', [
                BR,
                p('Photo of the Gold Medal')
            ]),
            card_img('2020 Diploma', '09/2020', '../files/oicat/diploma2020.jpg', [
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
            card_img('2020 Gold Medal', '09/2020', '../files/oicat/medal2020.jpg', [
                BR,
                p('Photo of the Gold Medal')
            ]),
        ])
    ]),
    award_semcv := Awards('/career/semcv', "Valencian Olympiad in Mathematics", 'SEMCV', '2013 — 2018', [
        'Third Prize in the 2018 edition',
        'Second Prize in the 2013 edition',
        'Reached final round in the 2014, 2015, 2016 & 2017 editions',
    ], [
        olympiad_titlecard('../files/semcv/logo.jpg', 'SEMCV Logo', 'Valencian Olympiad in Mathematics', 'Valencian Community, Spain', '2013 — 2018', a('https://semcv.org/', 'semcv.org')),
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
        p_no_margin("""
            Although the first phase is really short and simple (just a 2-hour exam), both the Provincial and Regional phases are much more drawn out,
            having many activities, several individual and team tests, lasting multiple days each.
        """),
        div('big-img',
            card_img_nohover(
                '../files/semcv/prize2018.jpg',
                f'Receiving the Third Prize of the 2018 edition in Viver, Valencia. {a('https://semcv.org/faseautonomica/olimpiades-autonomiques-anteriors/988-xxix-olimpiada-matematica-2018', 'Source')}',
                'Receiving the Third Prize of the 2018 edition in Viver, Valencia',
            )
        ),
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
        div('halfs limit-height', [
            card_img('2013 Diploma', '06/2013', '../files/semcv/diploma2013.jpg', [
                BR,
                p('Digital scan of the certificate (in Catalan).'),
                p('English translation:'),
                p("Olympiad in Mathematics"),
                p("Al-Khwarizmi Society for the Mathematical Education of the Valencian Community"),
                p("Diploma to Vicent Baeza Esteve for their participation in the Olympiad in Mathematics. Regional Phase"),
                p("Benidorm, 8th of June 2013"), 
                p("Provincial Coordinator"),
            ]),
            card_img('2014 Diploma', '06/2014', '../files/semcv/diploma2014.jpg', [
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
            card_img('2016 Diploma', '05/2016', '../files/semcv/diploma2016.jpg', [
                BR,
                p('Digital scan of the certificate (in Catalan).'),
                p('English translation:'),
                p("Olympiad in Mathematics"),
                p("Al-Khwarizmi Society for the Mathematical Education of the Valencian Community"),
                p("Diploma to Vicent Baeza Esteve for their participation in the Olympiad in Mathematics. Regional Phase"),
                p("Alicante, 29th of May 2016"),
                p("Provincial Coordinator"),
            ]),
            card_img('2017 Diploma', '05/2017', '../files/semcv/diploma2017.jpg', [
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
            card_img('2018 Diploma', '06/2018', '../files/semcv/diploma2018.jpg', [
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
for award in awards:
    generate(award.path, award.title, award.content)


# --------
# PROJECTS
# --------
class Project(Site):
    def __init__(self, path: str, title: str, institution: str, _date: str, keypoints: list[str], _tags: list[str], content: str | list[str] | None = None):
        super().__init__(path, title)
        self.institution = institution
        self.date = _date
        self.keypoints = keypoints
        self.tags = _tags
        self.content = content

projects : dict[str, list[Project]] = {
    'professional': [
        Project(f'{job_facephi.path}#tools', 'Automation & Data Scrapping Tools', 'Facephi', '09/2025 — Present', [
            'Built several automation & data scrapping tools leveraging AI agents.',
            'Extracted key information used to train production models.',
        ], ['Python', 'LangGraph', 'GitHub Actions']),
        Project(f'{job_compliancecms.path}#riskapp', 'RiskApp CMS', 'Compliance CMS', '12/2023 — 09/2025', [
            'Web application to automate corporate risk assessment.',
            'Design of the entire app & complete implementation from scratch.',
        ], ['PHP', 'JS', 'SQL']),
        Project(f'{job_compliancecms.path}#whistleblowing', 'Whistleblowing Channel', 'Compliance CMS', '07/2023 — 09/2025', [
            'Whistleblowing Channel compliant with Spanish & EU whistleblowing regulations.',
            'Planning, design, implementation & delivery of several key features.'
        ], ['PHP', 'JS', 'Vue.JS', 'SQL']),
    ],
    'university': [
        Project(f'{education_master.path}#final_project', 'Final Project', "Master's Degree in Data Science", '11/2024 — 06/2025', [
            'Exploration and testing of the Kolmogorov-Arnold architecture for neural networks.',
        ], ['ML', 'CNNs', 'Kolmogorov-Arnold Networks']),
        Project(f'{education_degree.path}#final_project', 'Final Project', 'Degree in Computer Engineering', '09/2023 — 05/2024', [
            'Research project exploring the applications of Quantum Computing in ML systems.',
        ], ['ML', 'Quantum Computing']),
        # Project(f'{education_degree.path}#last_brew', "The Last Brew", 'Degree in Computer Engineering', '07/2023 — 09/2023', [
        #     '2D game fully programmed in Z80 Assembly for the Amstrad CPC 8-bit computer.',
        #     'Fluid movement, collisions, projectiles, and multiple enemy types and behaviors.',
        # ], ['Z80 Assembly', 'Amstrad CPC', 'CPCTelera']),
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
generate('/projects', 'Projects', projects_content)

for project_type, project_type_projects in projects.items():
    for project in project_type_projects:
        if project.content is not None:
            generate(project.path, project.title, project.content)
        else:
            requested_local_paths.add(project.path)


# ----------
# MAIN PAGES
# ----------
generate("index", '', [
    h1("Vicent Baeza"),
    p("Software Engineer with a passion for math and computer science."),
    p(f"Currently building automation & data scrapping tools at {a(job_facephi.path, 'Facephi')}."),
    title_section('Work', [
        card(job.path, job.title, job.company, '', job.date, ul(job.keypoints))
        for job in jobs
    ], '/career#work', 3),
    title_section('Education', [
        card(education.path, education.title, education.institution, '', education.date, ul(education.keypoints))
        for education in [education_master, education_degree]
    ], '/career#education', 2),
    title_section('Contests & Awards', [
        card(award.path, award.title, award.institution, '', award.date, ul(award.keypoints))
        for award in awards
    ], '/career#awards', 3),
])

generate('/career', 'Career', [
    section('Work', 'work'),
    *[
        card(job.path, job.title, job.company, '', job.date, ul(job.keypoints) + taglist(job.tags))
        for job in jobs
    ],
    section('Education', 'education'),
    *[
        card(education.path, education.title, education.institution, '', education.date, ul(education.keypoints))
        for education in educations
    ],
    section('Awards', 'awards'),
    *[
        card(award.path, award.title, award.institution, '', award.date, ul(award.keypoints))
        for award in awards
    ]
])

# --------------
# GENERATE FILES
# --------------
word_trie = WordScoreTrie()
for word, scores in word_search_scores.items():
    word_trie.add(word, scores)

score_confs = list[list[int]]()
with open('docs/files/search_data.json', 'w', encoding='utf-8') as f:
    json.dump({
        'sites': search_sites,
        'score_confs': score_confs,
        'trie': word_trie.as_dict(score_confs, 5)['C'],
    }, f, indent=1)


# -----------------
# POST-BUILD CHECKS
# -----------------

# check site links
sites = list(paths.keys())
sites.append('/')
site_link_counts = {site: 0 for site in sites}
site_link_counts['/'] += 1
site_link_counts['index'] += 1
for site, site_paths in paths.items():
    for site_path in site_paths:
        path_fixed = '/' if site_path == '/' else site_path.strip('/') # remove start & end slashes, but keep them if path is '/'
        path_fixed = path_fixed.split('#', maxsplit=1)[0] # remove everything after '#': a/b#c -> a/b
        if is_local_path(path_fixed):
            if path_fixed in sites:
                site_link_counts[path_fixed] += 1
            elif f'/{path_fixed}' in sites:
                site_link_counts[f'/{path_fixed}'] += 1
            else:
                warnings[site].append(f"Invalid local path '{path_fixed}'")
for site, link_count in site_link_counts.items():
    if link_count == 0:
        warnings[site].append("Not linked in any other site")

# check requested local paths
for requested_local_path in requested_local_paths:
    if requested_local_path not in all_local_paths:
        path_without_id, path_id = requested_local_path.split('#', maxsplit=1)
        warnings.append(f"ID '{path_id}' not found")
        warnings.add(path_without_id)

# check files
for site, site_files in files.items():
    for site_file in site_files:
        file_path_fixed = remove_path_double_dots(site_file)
        if is_local_path(file_path_fixed):
            if not os.path.isfile(f'docs/{file_path_fixed}'):
                warnings[site].append(f"Invalid local file '{file_path_fixed}'")


# ----------------
# CONSOLE MESSAGES
# ----------------
print('Pages successfully built!')
any_warnings = False
for page, page_warnings in warnings.items():
    if len(page_warnings) > 0:
        any_warnings = True
        if len(page_warnings) == 1:
            print(f'⚠️  {page}: {page_warnings[0]}')
        else:
            print(f'⚠️  {page}:')
            for page_warning in page_warnings:
                print(f'  - {page_warning}')

if not any_warnings:
    print('✅ No warnings')
