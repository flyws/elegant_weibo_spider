#-*-coding:utf8-*-
import re
import os
import urllib
import requests
from lxml import etree
import time
import random


user_id = #THE ID YOU WANT TO GET DATA FROM

cookie = {"Cookie": "***********YOUR_COOKIE******************"}
headers = {'User-Agent': 'User-Agent:Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'}

url = 'https://weibo.cn/%d/profile' % user_id

html = requests.get(url, cookies = cookie, headers = headers).content
selector = etree.HTML(html)

raw_pageNum = selector.xpath('//*[@id="pagelist"]/form/div/text()[2]')[0]
pageNum = (int)(re.findall('/(\d*)', raw_pageNum)[0])

word_count = 1
image_count = 1

print(u'爬虫准备就绪...')

def get_text(text_list):
    if len(text_list) > 1:
        text = ''.join(text_list)
        text = text.replace('\u200b', '')
        return text
    text = text_list[0].replace('\u200b', '')
    return text

def get_img_urls(i):
    # need to differentiate how many pictures are inside, and if there's a location label
    is_img_exist = 1 if i.xpath('div[2]/a[2]/text()') == ['原图'] else 0
    is_more_than_one = 1 if (len(i.xpath('div[1]/a/text()')) != 0 and i.xpath('div[1]/a/text()')[0] != '显示地图') or \
                                (len(i.xpath('div[1]/a/text()')) > 1 and i.xpath('div[1]/a/text()')[0] == '显示地图') else 0
    if is_img_exist == 0:
        return 'No Pics'
    elif is_img_exist + is_more_than_one == 2:
        img_urls = i.xpath('div[1]/a/@href')
        # just in case there's any link in the text
        if len(img_urls) == 0:
            img_url = i.xpath('div[2]/a[2]/@href')[0]
            return img_url
        return img_urls
    elif is_img_exist + is_more_than_one == 1:
        img_url = i.xpath('div[2]/a[2]/@href')[0]
        return img_url
    
def explode_urls(urls):
    if isinstance(urls, str):
        return urls
    elif isinstance(urls, list):
        if len(urls) == 2:
            html = requests.get(urls[-1], cookies = cookie).content
        elif len(urls) == 1:
            html = requests.get(urls[0], cookies = cookie).content
        selector = etree.HTML(html)
        content = selector.xpath('/html/body/div/a[2]/@href')
        content = ['https://weibo.cn' + i for i in content]
        return content
        

def if_repost(i):
    div_list = i.xpath('div')
    # check if the reposted weibo has pictures inside
    is_img_exist = 1 if i.xpath('div[2]/a[2]/text()') == ['原图'] else 0
    if len(div_list) == 2 and is_img_exist == 1:
        # just in case the post has been deleted
        if i.xpath('div[1]/span[1]/text()')[0] == '转发了微博：':
            return [get_deleted_repost_reason_data]
        return [get_original_post_data]
    # for the case that it has only text in the repost
    elif len(div_list) == 2:
        # just in case the post has been deleted
        if i.xpath('div[1]/span[1]/text()')[0] in ['转发了微博：', '转发了\xa0']:
            return [get_deleted_repost_reason_data]
        return [get_repost_data, get_deleted_repost_reason_data]
    elif len(div_list) == 3:
        return [get_repost_data, get_repost_reason_data]
    elif len(div_list) == 1:
        return [get_plain_data]

# get original weibo with pictures       
def get_original_post_data(i):
    ## I need strings instead of list for the sake of browsing, others can make them to lists for
    ## the convenience of data analytics
    # deal with text
    text_list = i.xpath('div[1]/span/text()')
    text = get_text(text_list)
    # deal with metadata
    time_and_device_list = i.xpath('div[2]/span/text()')
    time_and_device = time_and_device_list[0].replace('\xa0', ' ')
    # deal with interaction data
    like_list = i.xpath('div[2]/a[3]/text()')
    repost_list = i.xpath('div[2]/a[4]/text()')
    comment_list = i.xpath('div[2]/a[5]/text()')
    interaction_list = [like_list[0], repost_list[0], comment_list[0]]
    interaction = ' '.join(interaction_list)
    return text, time_and_device, interaction

# get original script in the reposted weibo
def get_repost_data(i):
    # deal with text
    source = i.xpath('div[1]/span[1]/a/text()')[0]
    source_text = '转发了 ' + source + ' 的微博: '
    text_list = i.xpath('div[1]/span[2]/text()')
    text = get_text(text_list)
    text = source_text + text
    # deal with metadata, not applicable here
#     time_and_device_list = i.xpath('div[2]/span/text()')
#     time_and_device = time_and_device_list[0].replace('\xa0', ' ')
    # deal with interaction data
    like_list = i.xpath('div[2]/span[1]/text()')
    repost_list = i.xpath('div[2]/span[2]/text()')
    comment_list = i.xpath('div[2]/a[3]/text()')
    interaction_list = [like_list[0], repost_list[0], comment_list[0]]
    interaction = ' '.join(interaction_list)
    return text, interaction

# get my opinion in the reposted weibo
def get_repost_reason_data(i):
    # deal with text
    text_list = i.xpath('div[3]/span[1]/text()')
    text_list.append(i.xpath('div[3]/text()')[0].rstrip())
    text = get_text(text_list)
    # deal with metadata
    time_and_device_list = i.xpath('div[3]/span[2]/text()')
    time_and_device = time_and_device_list[0].replace('\xa0', ' ')
    # deal with interaction data
    like_list = i.xpath('div[3]/a[1]/text()')
    repost_list = i.xpath('div[3]/a[2]/text()')
    comment_list = i.xpath('div[3]/a[3]/text()')
    interaction_list = [like_list[0], repost_list[0], comment_list[0]]
    interaction = ' '.join(interaction_list)
    return text, time_and_device, interaction

# post that has no pictures
def get_plain_data(i):
    # deal with text
    text_list = i.xpath('div[1]/span[1]/text()')
    text = get_text(text_list)
    # check if external link exists
    if len(i.xpath('div[1]/span[1]/a/text()')) != 0:
        text = text + i.xpath('div[1]/span[1]/a/text()')[0]
    # deal with metadata
    time_and_device_list = i.xpath('div[1]/span[2]/text()')
    time_and_device = time_and_device_list[0].replace('\xa0', ' ')
    # deal with interaction data
    like_list = i.xpath('div[1]/a[1]/text()')
    repost_list = i.xpath('div[1]/a[2]/text()')
    comment_list = i.xpath('div[1]/a[3]/text()')
    interaction_list = [like_list[0], repost_list[0], comment_list[0]]
    interaction = ' '.join(interaction_list)
    return text, time_and_device, interaction

# get deleted repost weibo
def get_deleted_repost_reason_data(i):
    # deal with text
    text_list = i.xpath('div[2]/span[1]/text()')
    text_list.append(i.xpath('div[2]/text()')[0].rstrip())
    text = get_text(text_list)
    # deal with metadata
    time_and_device_list = i.xpath('div[2]/span[2]/text()')
    time_and_device = time_and_device_list[0].replace('\xa0', ' ')
    # deal with interaction data
    like_list = i.xpath('div[2]/a[1]/text()')
    repost_list = i.xpath('div[2]/a[2]/text()')
    comment_list = i.xpath('div[2]/a[3]/text()')
    interaction_list = [like_list[0], repost_list[0], comment_list[0]]
    interaction = ' '.join(interaction_list)
    return text, time_and_device, interaction


user_folder_path = os.getcwd() + "/%s" % (user_id)
if os.path.exists(user_folder_path) is False:
    os.mkdir(os.getcwd() + "/%s" % (user_id))

image_folder_path = os.getcwd() + "/%s/images" % (user_id)
if os.path.exists(image_folder_path) is False:
    os.mkdir(os.getcwd() + "/%s/images" % (user_id))

# add below code to fake browser's behavior for urllib package that is being used later
opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'User-Agent:Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36')]
urllib.request.install_opener(opener)    

for page in range(29, pageNum+1):

    #获取lxml页面
    url = 'https://weibo.cn/%d/profile?page=%d' % (user_id, page)
    s = requests.Session()
    lxml = s.get(url, cookies = cookie, headers = headers).content

    #文字爬取
    selector = etree.HTML(lxml)
    content = selector.xpath('//*[@class="c"]')[0:10]
    result = ''
    url_list = []
    for i in content:
        # in case there're not full 10 posts in last page
        if i.xpath('text()[1]') == ['设置:']:
            break
        extract_func = if_repost(i)
        if len(extract_func) == 2:     
            repost_data = extract_func[1](i)
            result += '\r\n'.join(repost_data) + '\r\n'
        original_data = extract_func[0](i)
        result += '\r\n'.join(original_data) + '\r\n'
        # clean up urls to retrieve photos later
        if isinstance(explode_urls(get_img_urls(i)), list):
            url_list.extend([i for i in explode_urls(get_img_urls(i))])
        if isinstance(explode_urls(get_img_urls(i)), str) and explode_urls(get_img_urls(i)) != 'No Pics':
            url_list.append(explode_urls(get_img_urls(i)))
        # attach a simple link back to each post
        result += '\r\n'.join(explode_urls(get_img_urls(i))) + '\r\n\r\n' if \
                        isinstance(explode_urls(get_img_urls(i)), list) else explode_urls(get_img_urls(i)) + '\r\n\r\n'
    with open(user_folder_path + "/page%d.txt" % (page), 'w') as f:    
        f.write(result)
        
    # get images
    for i in range(1, len(url_list)+1):
        temp = image_folder_path + '/%d_%s.jpg' % (page, i)
        print('Waiting to download picture no.%a in page %d......' % (i, page))
        # below is for those X Large photos which require extra second step
        temp_session = s.get(url_list[i-1], cookies = cookie, headers = headers)
        link = temp_session.url
        webpage = temp_session.content
        selector = etree.HTML(webpage)
        if len(selector.xpath('/html/body/div')) == 4:
            link = selector.xpath('/html/body/div[3]/a[1]/@href')[0]
            link = s.get(link, cookies = cookie, headers = headers).url
        urllib.request.urlretrieve(link, temp)
        time.sleep(random.randrange(5,15))
    print('Simulating human behavior, cleaning up results from page {}'.format(page))
    time.sleep(random.randrange(10,20))

print('SUCCESS: all weibo posts and images from user %d are downloaded' % (user_id)) 
