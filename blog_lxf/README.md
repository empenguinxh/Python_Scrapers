

脚本 download_tutorial_python.py 下载廖雪峰老师的python教程，所有的网页、图片、视频都保存在当前文件路径下的htmls文件夹内。

download_tutorial_javascript.py、download_tutorial_git.py都基于download_tutorial_python.py生成，分别下载如后缀名所示的教程。

脚本 convert_to_epub_python.py使用ebooklib将html文件转换为epub。
convert_to_epub_javascript.py、convert_to_epub_git.py类似

详情见download_blog.md，里面有细致的代码说明，以及epub的制作过程。

另外，epub内不支持观看大于1MB的视频。所以git教程内的许多视频无法观看。

移动设备上推荐使用多看阅读器。其他软件会显示不正常。