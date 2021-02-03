from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import time
import json
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import os
import urllib.request
from tqdm import tqdm
import datetime

caps = DesiredCapabilities.CHROME
caps['goog:loggingPrefs'] = {'performance': 'ALL'}

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--mute-audio")

driver = webdriver.Chrome(desired_capabilities=caps, options = chrome_options)

page = "https://www.vlive.tv/channel/C1B7AF/board/5464"

driver.get(page)

for i in range(1, 60):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

html = driver.page_source

soup = BeautifulSoup(html, 'html.parser')
videos = soup.find_all('li', {'class': 'post_item--3Brrv'})

links = []
for video in videos:
    link = video.find('a', {'class': 'post_area--3dKbo'}).attrs['href']
    links.append(link)

print('# of videos found: ' + str(len(links)))

# links.reverse()

def process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response

for vlive in tqdm(links):
    attempts = 0

    r = requests.get("https://vlive.tv"+vlive)
    get_request_soup = BeautifulSoup(r.text, 'html.parser')

    script = get_request_soup.find('script', {'type': 'text/javascript'}).text.replace('window.__PRELOADED_STATE__=', "").split(',function', 1)[0]
    video_obj = json.loads(script)

    video_id = str(video_obj['postDetail']['post']['officialVideo']['videoSeq'])
    title = video_obj['postDetail']['post']['title']
    date = datetime.datetime.fromtimestamp(video_obj['postDetail']['post']['createdAt']/1000).strftime("%Y%m%d%H%M")
    print(date, video_id, title)

    video_path = "D:/izone/" + date + '_' + video_id

    driver.get("https://vlive.tv/video/"+video_id)
    time.sleep(5)
    video_html = driver.page_source

    while attempts < 5:
        #handles unexpected page load failures
        try:
            browser_log = driver.get_log('performance')
            events = [process_browser_log_entry(entry) for entry in browser_log]
            new_events = []

            for event in events:
                try:
                    if 'apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0' in event['params']['request']['url']:
                        new_events.append(event)
                except:
                    pass
            if not len(new_events) == 0:
                naver_link = new_events[0]['params']['request']['url'][0:177]
                naver_r = requests.get(naver_link).json()
                video_res = naver_r['videos']['list']
                sorted_video_res = sorted(video_res, key = lambda k: k['encodingOption']['height'])
                video_link = sorted_video_res[-1]['source']
            else:
                driver.refresh()
                attempts+=1
            break
        except:
            driver.refresh()
            attempts+=1
    

    video_attempts = 0

    if os.path.exists(video_path):
        for roots, dirs, files in os.walk(video_path):
            if 'captions' in naver_r:
                #if the video has captions
                for language in naver_r['captions']['list']:
                    code_and_type = language['language'] + '-' + language['type']
                    sub_link = language['source']
                    # if not any(code_and_type in i for i in dirs):
                    if not os.path.exists(video_path + '/' + code_and_type + '/'):
                        os.mkdir(video_path + '/' + code_and_type)
                        urllib.request.urlretrieve(sub_link, video_path + '/' + code_and_type + '/' + code_and_type + ".vtt")
                        print('Acquired ' + code_and_type + '.vtt')

            if not any('.mp4' in x for x in files):
                #no video
                while video_attempts < 5:
                    try:
                        urllib.request.urlretrieve(video_link, video_path + '/' + video_id + '.mp4')
                        print('Acquired ' + video_id + '.mp4')
                        break
                    except:
                        video_attempts += 1
                        pass

            if not 'title.txt' in files:
                #no title
                with open(video_path + '/' + 'title.txt', 'w', encoding = 'utf-8') as f:
                    f.write(title)
            
            #top level dir
            break

    else:
        matching_id_dir = [x for x in os.listdir("D:/izone/") if video_id in x.split("_")[1]]
        if not len(matching_id_dir) == 0:
            matching_id_date = matching_id_dir[0].split("_")[0]
            if not matching_id_date == date:
                print('SAME VIDEO ID EXISTS, DIFFERENT DATE: ', date, video_id)
                print(matching_id_dir[0])
                break

        os.mkdir(video_path)
        while video_attempts < 5:
            try:
                urllib.request.urlretrieve(video_link, video_path + '/' + video_id+'.mp4')
                print('Acquired ' + video_id + '.mp4')
                break
            except:
                video_attempts += 1
                pass


        if 'captions' in naver_r:
            #if video has captions
            for language in naver_r['captions']['list']:
                code_and_type = language['language'] + '-' + language['type']
                sub_link = language['source']
                os.mkdir(video_path + '/' + code_and_type)
                urllib.request.urlretrieve(sub_link, video_path + '/' + code_and_type + '/' + code_and_type + ".vtt")
                print('Acquired ' + code_and_type + '.vtt')

        with open(video_path + '/' + 'title.txt', 'w', encoding = 'utf-8') as f:
            f.write(title)
    