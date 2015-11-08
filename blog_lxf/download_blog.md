
# 引子

廖雪峰老师的在线教程系列很不错，这个notebook尝试着将其中的[python系列](http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000)下载到本地。

该脚本将python教程的每个章节单独存为本地的html文档，以`chapter0.html`、`chapter1.html`等形式命名。同时，图片本地化、代码高亮化。

开始之前搜索了网上现成的脚本，除了[抓取廖雪峰的Git教程](http://crossin.me/forum.php?mod=viewthread&tid=724)外，其他的思路都不清晰。

本文的基本思路仿照那个帖子，先从目录页抽取所有章节的网址，然后使用beautifulsoup抓取有用的内容，即`<div class="x-wiki-content">...</div>`之间的内容，最后输出成网页。

另外，本文还涵盖了epub的制作过程。


```python
%run sync_to_file_magic_command.py
```


```python
script_file = 'download_tutorial.py'
```


```python
%%sync_to_file $script_file -m o
import os
import requests
import codecs
import json
from bs4 import BeautifulSoup
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from multiprocessing.dummy import Pool as ThreadPool
```


```python
from PIL import Image
from StringIO import StringIO
```


```python
%%sync_to_file $script_file
website_domain = 'http://www.liaoxuefeng.com'
parent_folder = 'htmls'
```

# 抓取目录页

将所有的章节名和章节链接存放在变量`content_url_l`。


```python
home_page_url = 'http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000'
tmp_r = requests.get(home_page_url)
```


```python
tmp_home_soup = BeautifulSoup(tmp_r.content, 'lxml')
tmp_content_ul = tmp_home_soup.find('ul', {'class':'uk-nav uk-nav-side', 'style':'margin-right:-15px;'})
```


```python
content_url_l = []
for tmp_index, tmp_content_a in enumerate(tmp_content_ul.find_all('a')):
    content_url_l.append((tmp_content_a.text, tmp_content_a['href']))
```


```python
# test
def unit_test(test_index):
    print content_url_l[test_index][0], '\n', content_url_l[test_index][1]
unit_test(4)
del unit_test
print '%d chapters in total'%len(content_url_l)


def unit_test(test_index):
    test_content_url = website_domain + content_url_l[test_index][1]
    print content_url_l[test_index][0]
    print test_content_url
    test_soup = BeautifulSoup(requests.get(test_content_url).content, 'lxml')
    print test_soup
# unit_test(10)
del unit_test
```

    第一个Python程序 
    /wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000/001431611988455689d4c116b2c4ed6aec000776c00ed52000
    123 chapters in total
    

# 处理单个章节

这一部分，通过一步步实验，写出的最终函数具有如下功能。读入一个网址，将网页的正文部分提取出来。处理过程中，css、图片以及视频都会本地化。

使用[使用list和tuple](http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000/0014316724772904521142196b74a3f8abf93d8e97c6ee6000)一节作为探索。因为这节既有图片又有代码。

正文的内容很好提取，在`<div class='x-wiki-content'>`...`</div>`之间。

图片稍微麻烦一些。原本的图片是没有扩展名的，但其字节码中（头部）应该指示了文件解码该用的格式（PNG）。python内，采用'wb'模式，直接把得到的字节码写为文件。

css部分，由于我们只关注正文的内容，除了代码高亮外，其他的格式都不需要。而代码部分，用request得到的网页只有`<code>...</code>`之间的原始内容，未经渲染，没有语法高亮。这里手动使用pygments来加高亮并替换原文内容。


```python
test_url = website_domain + content_url_l[11][1]
test_soup = BeautifulSoup(requests.get(test_url).content, 'lxml')
test_wiki_content = test_soup.find('div', {'class': 'x-wiki-content'})
```

## 处理图片


```python
test_img_url = test_wiki_content.img['src']
print test_wiki_content.img
print test_img_url
```

    <img alt="tuple-0" src="/files/attachments/001387269705541ad608276b6f7426ca59b8c2b19947243000/0"/>
    /files/attachments/001387269705541ad608276b6f7426ca59b8c2b19947243000/0
    


```python
test_image_bc = requests.get(website_domain+test_img_url).content
test_image = Image.open(StringIO(test_image_bc))
print test_image.format
```

    PNG
    


```python
# test
def unit_test():
    test_img_url = test_wiki_content.img['src']
    test_image_bc = requests.get(website_domain+test_img_url).content
    test_dir = os.path.dirname(test_img_url[1:])
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    with open(test_img_url[1:], 'wb') as f:
        f.write(test_image_bc)
    test_wiki_content.img['src'] = test_img_url[1:]
    with codecs.open('test_html.html', 'w', encoding='utf-8') as f:
        f.write(test_wiki_content.prettify())
#unit_test()
del unit_test
```

## 高亮代码

将pygments提供的css源码保存为文件


```python
with codecs.open('styles.css', 'w', encoding='utf-8') as f:
    f.write(HtmlFormatter().get_style_defs('.highlight'))
```

得到html源码并转换为soup对象后，首先从code标签中提取内容，用pygments高亮。但转换后得到的是字符串，需要先转换为临时soup，再用这个临时soup替换原soup中的相应部分。

替换时，使用soup的replace_with方法。


```python
test_code_block = test_wiki_content.find('code')
```


```python
print test_code_block.get_text()
test_highlight = highlight(test_code_block.get_text(), PythonLexer(), HtmlFormatter())
print test_highlight
test_highlight_soup = BeautifulSoup(test_highlight, 'lxml').div
print 'Convert', type(test_highlight), 'to', type(test_highlight_soup)
```

    >>> classmates = ['Michael', 'Bob', 'Tracy']
    >>> classmates
    ['Michael', 'Bob', 'Tracy']
    
    <div class="highlight"><pre><span class="o">&gt;&gt;&gt;</span> <span class="n">classmates</span> <span class="o">=</span> <span class="p">[</span><span class="s">&#39;Michael&#39;</span><span class="p">,</span> <span class="s">&#39;Bob&#39;</span><span class="p">,</span> <span class="s">&#39;Tracy&#39;</span><span class="p">]</span>
    <span class="o">&gt;&gt;&gt;</span> <span class="n">classmates</span>
    <span class="p">[</span><span class="s">&#39;Michael&#39;</span><span class="p">,</span> <span class="s">&#39;Bob&#39;</span><span class="p">,</span> <span class="s">&#39;Tracy&#39;</span><span class="p">]</span>
    </pre></div>
    
    Convert <type 'unicode'> to <class 'bs4.element.Tag'>
    


```python
# test
def unit_test():
    _ = test_code_block.replace_with(test_highlight_soup)
    with codecs.open('test_html.html', 'w', encoding='utf-8') as f:
        header = '<!DOCTYPE html>\n<head>\n<link rel="stylesheet" href="styles.css">\n</head>\n<body>'
        f.write(header)
        f.write(test_wiki_content.prettify())
        f.write('</body>')
#unit_test()
del unit_test
```

## 下载视频

以章节[定义函数](http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000/001431679203477b5b364aeba8c4e05a9bd4ec1b32911e2000)为例


```python
test_url = website_domain + content_url_l[17][1]
test_html_str = requests.get(test_url).content
```


```python
def unit_test():
    test_soup = BeautifulSoup(test_html_str, 'lxml')
    test_wiki_content = test_soup.find('div', {'class': 'x-wiki-content'})
    for video_index, video_tag in enumerate(test_wiki_content.find_all('video')):
        source_tag = video_tag.source
        github_url = source_tag.source['src']
        source_tag.clear()
        video_bc = requests.get(github_url).content
        video_save_file_name = 'test_video_{}.mp4'.format(video_index)
        with open(video_save_file_name, 'wb') as f:
            f.write(video_bc)
        source_tag['src'] = video_save_file_name
        print source_tag
    with codecs.open('test_html.html', 'w', encoding='utf-8') as f:
        f.write(test_wiki_content.prettify())
#unit_test()
del unit_test
```

## 整合

一般图片都是放在某个文件夹下，以“0”命名。

但有的网页，比如[Day 9 - 编写API](http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000/0014323391480651a75b5fda4cb4c789208191682fc2c70000)，图片地址为`/files/attachments/001402403872210f486e3db3d4f4314acbfc0cc97006b32000/`，没有具体的文件名。

所以，将图片地址按照'/'拆分，取倒数第二个子串。

另外，所有图片的上级文件夹都按照所属章节的序号统一命名。

最后，由于使用多进程，很可能出现两个以上的进程同时要创建同一个文件夹的情形。所以采用try的形式，忽略无权限的问题。


```python
%%sync_to_file $script_file
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
```


```python
%%sync_to_file $script_file
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
```


```python
%%sync_to_file $script_file
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
        highlight_str = highlight(code_tag.get_text(), PythonLexer(), HtmlFormatter())
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
```

访问网址并取回内容这一步，由于我不会协程，所以采用很笨的方法，一旦出错，就递归调用函数重试。

`-!-`表示服务器响应了，但返回的是`503 Service Temporarily Unavailable`。`+`表示成功取得正文内容。

如果只是urlib超过最大重试次数，提示'r'。


```python
%%sync_to_file $script_file
def get_chap_soup(chap_url):
    success = False
    try:
        chap_soup = BeautifulSoup(requests.get(website_domain + chap_url).content, 'lxml')
        success = True
    except:
        print 'r',
        chap_soup = get_chap_soup(chap_url)
    if chap_soup.title.get_text() == '503 Service Temporarily Unavailable':
        chap_soup = get_chap_soup(chap_url)
        success = False
        print '-!-',
    if success:
        print '+',
    return chap_soup
```


```python
def unit_test(test_index):
    print 'Processing chapter', content_url_l[test_index][0]
    chap_url = content_url_l[test_index][1]
    chap_soup = get_chap_soup(chap_url)
    pool = ThreadPool(4)
    test_html = process_one_chapter(chap_soup, pool, test_index)
    with codecs.open(parent_folder + '/test_html.html','w',encoding='utf-8') as f:
        f.write(test_html)
#unit_test(17)
del unit_test
```

# 下载整个教程

因为ipython不支持python原生的多进程、多线程模块，所以将代码写入脚本，然后直接运行。

因为并发处理的不好，所以很可能在下载网页或图片时卡住。多运行几次就好了。


```python
%%sync_to_file $script_file
def get_soup_l():
    home_page_url = 'http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000'
    home_soup = BeautifulSoup(requests.get(home_page_url).content, 'lxml')
    content_ul = home_soup.find('ul', {'class':'uk-nav uk-nav-side', 'style':'margin-right:-15px;'})
    content_title_l = []
    content_url_l = []
    for _index, content_a in enumerate(content_ul.find_all('a')):
        content_url_l.append(content_a['href'])
        content_title_l.append(content_a.text)
    pool = ThreadPool(8)
    chap_soup_l = pool.map(get_chap_soup, content_url_l)
    '''
    chap_soup_l = []
    for content_url in content_url_l:
        chap_soup_l.append(get_chap_soup(content_url))
    '''
    return chap_soup_l
```


```python
%%sync_to_file $script_file
def get_html_l(chap_soup_l):
    html_l = []
    if not os.path.isdir(parent_folder):
        os.makedirs(parent_folder)
    for chap_index, chap_soup in enumerate(chap_soup_l):
        pool = ThreadPool(6)
        one_html = process_one_chapter(chap_soup, pool, chap_index)
        html_l.append(one_html)
        # write to file
        file_name = parent_folder + '\chapter_' + unicode(chap_index) + '.html'
        with codecs.open(file_name, 'w', encoding='utf-8') as f:
            f.write(one_html)
        print chap_index,
    return html_l
```


```python
%%sync_to_file $script_file -p
if __name__ == '__main__':
    soup_l_file = 'soup_l_file.txt'
    html_l_file = 'html_l_file.txt'
    if not os.path.isfile(soup_l_file):
        _soup_l = get_soup_l()
        _soup_l_str_l = [_soup.prettify() for _soup in _soup_l]
        with open(soup_l_file, 'w') as f:
            json.dump(_soup_l_str_l, f, indent=4)
    else:
        with open(soup_l_file, 'r') as f:
            _soup_l = [BeautifulSoup(html_str, 'lxml') for html_str in json.load(f, encoding='utf-8')]
    print '\n convert to html'
    _html_l = get_html_l(_soup_l)
    with open(html_l_file, 'w') as f:
        json.dump(_html_l, f, indent=4)
```

# 转换为epub

到这一步，当前目录下应该有一个htmls文件夹，里面有`chapter_0.html`至`chapter_122.html`以及相应的图片文件夹。

另外，还有两个文件。一个是`soup_l_file.txt`，存放的是未处理的html源码，另一个是`html_l_file.txt`，包含处理过的html源码。


这一步使用模块[ebooklib](https://github.com/aerkalov/ebooklib)

## 更详细的目录

既然要做成epub，那么原先扁平式的目录就不够用了。原教程中，通过缩进的方式，区分了目录的层级。

原教程最多有三级目录，比如“函数式编程”->“高级函数”->“map/reduce”。这里为了便于浏览，只保留前两级目录。


```python
home_page_url = 'http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000'
home_html_str = requests.get(home_page_url).content
```


```python
def get_detailed_content():
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
```


```python
first_level_indicator_l = get_detailed_content()
```

## 转换为epub


```python
from ebooklib import epub
```


```python
with open('html_l_file.txt', 'r') as f:
    html_str_l = json.load(f, encoding='utf-8')
```


```python
book = epub.EpubBook()
# set metadata
book.set_identifier('id123456')
book.set_language('cn')
book.set_title(u'Python教程')
book.add_author(u'廖雪峰')
get_title = lambda _str: re.compile('<h4>(.*)</h4>').search(_str).group(1)

toc_list = []
spine_list = ['cov', 'nav']

# add css
hight_css = epub.EpubItem(uid="style_nav", file_name="style.css", media_type="text/css")
hight_css.content = open('styles.css', 'r').read()
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
    chap_pic_dir = 'htmls/' + chap_uid
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
#book.set_cover("image.png", pic_stream)
book.spine = spine_list
# write to the file
epub.write_epub('test.epub', book, {})
```


```python

```
