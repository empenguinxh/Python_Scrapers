# coding: utf-8
import os
import requests
import json
from bs4 import BeautifulSoup
import re
from ebooklib import epub
tutorial_name = 'python'
home_page_url = '/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000'

website_domain = 'http://www.liaoxuefeng.com'
tutorial_name_prefix = tutorial_name + '_'
temp_folder = tutorial_name_prefix + 'temp'
parent_folder = tutorial_name_prefix + 'htmls'
def get_detailed_content():
    home_html_str = requests.get(website_domain + home_page_url).content
    home_soup = BeautifulSoup(home_html_str, 'lxml')
    content_ul = home_soup.find('ul', {'class':'uk-nav uk-nav-side', 'style':'margin-right:-15px;'})
    is_first_level_l = []
    for li_tag in content_ul.find_all('li'):
        if li_tag.has_attr('style'):
            indent_style = li_tag['style']
            if indent_style.endswith('1em;'):
                is_first_level_l.append(True)
            else:
                is_first_level_l.append(False)
        else:
            is_first_level_l.append(True)
    return is_first_level_l

first_level_indicator_l = get_detailed_content()
html_l_file_name = tutorial_name_prefix + 'html_l_file.txt'

with open(html_l_file_name, 'r') as f:
    html_str_l = json.load(f, encoding='utf-8')
    
title = tutorial_name.capitalize() + u'教程'
author = u'廖雪峰'
epub_name = '{}_tutorial.epub'.format(tutorial_name)
book = epub.EpubBook()
# set metadata
#book.set_identifier('id123456')
book.set_language('cn')
book.set_title(title)
book.add_author(author)
get_title = lambda _str: re.compile('<h4>(.*)</h4>').search(_str).group(1)

toc_list = []
spine_list = ['cov', 'nav']

# add css
hight_css = epub.EpubItem(uid="style_nav", file_name="style.css", media_type="text/css")
hight_css.content = open(parent_folder + '/styles.css', 'r').read()
book.add_item(hight_css)

section_list = None
for chap_index, html_str in enumerate(html_str_l):
    chap_title = get_title(html_str)
    chap_uid = 'chapter_{:d}'.format(chap_index)
    chap_file_name = chap_uid + '.xhtml'
    # create chapter
    one_chap = epub.EpubHtml(title=chap_title, file_name=chap_file_name, lang='cn', content=html_str)
    one_chap.add_item(hight_css)
    # add chapter
    book.add_item(one_chap)
    # toc
    if first_level_indicator_l[chap_index]:
        if not (section_list is None):
            toc_list.append(section_list)
        section_list = []
        section_list.append(epub.Section(chap_title))
        section_list.append([])
        section_list[1].append(one_chap)
    else:
        section_list[1].append(one_chap)
    #toc_list.append(epub.Link(chap_file_name, chap_title, chap_uid))
    # spine
    spine_list.append(one_chap)
    # add picture and video
    chap_pic_dir = parent_folder + '/' + chap_uid
    if os.path.exists(chap_pic_dir):
        for media_file_name in os.listdir(chap_pic_dir):
            media_file_full_path = chap_pic_dir + '/' + media_file_name
            media_file_save_path = chap_uid + '/' + media_file_name
            media_data = open(media_file_full_path, 'rb').read()
            if media_file_name.endswith('mp4'):
                # video
                media_type = 'video/mp4'
            else:
                # pic
                media_type = 'image/png'
            one_media = epub.EpubItem(uid=media_file_name,  file_name=media_file_save_path, 
                                      media_type=media_type, content=media_data)
            book.add_item(one_media)
toc_list.append(section_list)

# define Table Of Contents
book.toc = toc_list

# add default NCX and Nav file
book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

# define css style
style = '''
@namespace epub "http://www.idpf.org/2007/ops";
body {
    font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
}
h2 {
     text-align: left;
     text-transform: uppercase;
     font-weight: 200;     
}
ol {
        list-style-type: none;
}
ol > li:first-child {
        margin-top: 0.3em;
}
nav[epub|type~='toc'] > ol > li > ol  {
    list-style-type:square;
}
nav[epub|type~='toc'] > ol > li > ol > li {
        margin-top: 0.3em;
}
'''

# add css file
nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
book.add_item(nav_css)


# basic spine
#book.set_cover("image.png", pic_data)
book.spine = spine_list
# write to the file
epub.write_epub(epub_name, book, {})
