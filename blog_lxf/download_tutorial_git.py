# coding: utf-8
import os
import requests
import json
from bs4 import BeautifulSoup
import codecs
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from multiprocessing.dummy import Pool as ThreadPool
tutorial_name = 'git'
home_page_url = '/wiki/0013739516305929606dd18361248578c67b8067c8c017b000'

website_domain = 'http://www.liaoxuefeng.com'
tutorial_name_prefix = tutorial_name + '_'
temp_folder = tutorial_name_prefix + 'temp'
parent_folder = tutorial_name_prefix + 'htmls'
lexer = get_lexer_by_name('ruby')
def process_one_img(par_tuple):
    img_tag, chap_index = par_tuple
    img_src = img_tag['src']
    if not img_src.startswith('/files'):
        img_tag['src'] = ''
        return
    sub_str_l = img_src.split('/')
    img_rel_path = 'chapter_' + unicode(chap_index) + '/' + sub_str_l[-2]
    if not (sub_str_l[-1] is None):
        img_rel_path += '_' + sub_str_l[-1]
    img_full_path = parent_folder + '/' + img_rel_path
    if not os.path.isfile(img_full_path):
        img_dir = os.path.dirname(img_full_path)
        try:
            if not os.path.exists(img_dir):
                os.makedirs(img_dir)
        except WindowsError:
            pass
        img_bc = requests.get(website_domain + img_src).content
        with open(img_full_path, 'wb') as f:
            f.write(img_bc)
    img_tag['src'] = img_rel_path
def process_one_chapter(chap_soup, pool, chap_index):
    chap_wiki_content = chap_soup.find('div', {'class': 'x-wiki-content'})
    if chap_wiki_content is None:
        print chap_soup.prettify()
    # save img and use multithread
    par_l = [(img_tag, chap_index) for img_tag in chap_wiki_content.find_all('img')]
    _ = pool.map(process_one_img, par_l)
    # highlight code
    for code_tag in chap_wiki_content.find_all('code'):
        if code_tag.parent.name != 'pre':
            # skip inline code
            continue
        highlight_str = highlight(code_tag.get_text(), lexer, HtmlFormatter())
        highlight_div = BeautifulSoup(highlight_str, 'lxml').div
        _ = code_tag.replace_with(highlight_div)
    # save video
    process_video(chap_wiki_content, chap_index)
    # generate html
    header = '<!DOCTYPE html>\n<head>\n<meta charset="utf-8"/>\n<link rel="stylesheet" href="styles.css">\n'
    header += '<title>' + chap_soup.title.get_text().strip() + '</title>\n</head>\n<body>'
    header += '\n<h4>' + chap_soup.h4.get_text().strip() + '</h4>\n'
    html_str = header + chap_wiki_content.prettify() + '</body>'
    return html_str
def process_video(chap_wiki_soup, chap_index):
    for video_index, video_tag in enumerate(chap_wiki_soup.find_all('video')):
        source_tag = video_tag.source
        github_url = source_tag.source['src']
        video_rel_path = 'chapter_{}/chapter_{}_video_{}.mp4'.format(chap_index, chap_index, video_index)
        video_full_path = parent_folder + '/' + video_rel_path
        video_dir = os.path.dirname(video_full_path)
        source_tag['src'] = video_rel_path
        source_tag.clear()
        if os.path.isfile(video_full_path):
            continue
        video_bc = requests.get(github_url).content
        if not os.path.exists(video_dir):
            os.makedirs(video_dir)
        with open(video_full_path, 'wb') as f:
            f.write(video_bc)
def get_chap_soup(chap_url, use_cache=True):
    chap_temp_file_name = chap_url.replace('/', '_')
    chap_temp_file_full_path = temp_folder + '/' + chap_temp_file_name

    if use_cache and os.path.isfile(chap_temp_file_full_path):
        print '-cache-',
        with codecs.open(chap_temp_file_full_path, 'r', encoding='utf-8') as f:
            chap_soup = BeautifulSoup(f.read(), 'lxml')
        return chap_soup

    while True:
        try:
            r = requests.get(website_domain + chap_url, timeout=10)
        except requests.ConnectionError:
            print '-ce-',
        except requests.Timeout:
            print '-t-',
        else:
            if r.status_code == 503:
                print '-503-',
            else:
                print '+',
                chap_soup = BeautifulSoup(r.content, 'lxml')
                break

    if use_cache:
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
        with codecs.open(chap_temp_file_full_path, 'w', encoding='utf-8') as f:
            f.write(r.content.decode('utf-8'))

    return chap_soup
def get_soup_l():
    home_soup = BeautifulSoup(requests.get(website_domain + home_page_url).content, 'lxml')
    content_ul = home_soup.find('ul', {'class':'uk-nav uk-nav-side', 'style':'margin-right:-15px;'})
    content_title_l = []
    content_url_l = []
    for _index, content_a in enumerate(content_ul.find_all('a')):
        content_url_l.append(content_a['href'])
        content_title_l.append(content_a.text)
    pool = ThreadPool(4)
    chap_soup_l = pool.map(get_chap_soup, content_url_l)
    return chap_soup_l
def get_html_l(chap_soup_l):
    html_l = []
    if not os.path.isdir(parent_folder):
        os.makedirs(parent_folder)
    for chap_index, chap_soup in enumerate(chap_soup_l):
        pool = ThreadPool(6)
        one_html = process_one_chapter(chap_soup, pool, chap_index)
        html_l.append(one_html)
        # write to file
        file_name = parent_folder + '/chapter_' + unicode(chap_index) + '.html'
        with codecs.open(file_name, 'w', encoding='utf-8') as f:
            f.write(one_html)
        print chap_index,
    return html_l
if __name__ == '__main__':
    if not os.path.exists(parent_folder):
        os.makedirs(parent_folder)
    print '\n Get htmls'
    soup_l_file = tutorial_name_prefix + 'soup_l_file.txt'
    html_l_file = tutorial_name_prefix + 'html_l_file.txt'
    if not os.path.isfile(soup_l_file):
        _soup_l = get_soup_l()
        _soup_l_str_l = [_soup.prettify() for _soup in _soup_l]
        with open(soup_l_file, 'w') as f:
            json.dump(_soup_l_str_l, f, indent=4)
    else:
        with open(soup_l_file, 'r') as f:
            _soup_l = [BeautifulSoup(html_str, 'lxml') for html_str in json.load(f, encoding='utf-8')]
    with codecs.open(parent_folder + '/styles.css', 'w', encoding='utf-8') as f:
        f.write(HtmlFormatter().get_style_defs('.highlight'))
    print '\n Convert to html'
    _html_l = get_html_l(_soup_l)
    with open(html_l_file, 'w') as f:
        json.dump(_html_l, f, indent=4)
