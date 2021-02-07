from bs4 import BeautifulSoup
import requests
import time
import json
import os
import urllib.request
from tqdm import tqdm
import datetime

# different length because of VLive RememVer party (playlist not a video) + 2 IDOL ROOM playlists (just playlists, but videos within the playlist also appear in the total list)
# all_vlives_endpoint = "http://api.vfan.vlive.tv/vproxy/channelplus/getChannelVideoList?app_id=8c6cc7b45d2568fb668be6e05b6e5a3b&channelCode=C1B7AF&maxNumOfRows=1000"
# video_list_r = requests.get(all_vlives_endpoint).json()
# links = [str(obj['videoSeq']) for obj in video_list_r['result']['videoList']]

headers = {
    'Referer': "https://www.vlive.tv/channel/C1B7AF/board/5464"
}

all_vlives_endpoint = "https://www.vlive.tv/globalv-web/vam-web/post/v1.0/board-5464/posts?appId=8c6cc7b45d2568fb668be6e05b6e5a3b&fields=attachments,author,availableActions,board%7BboardId,title,boardType,payRequired,includedCountries,excludedCountries%7D,channel%7BchannelName,channelCode%7D,commentCount,contentType,createdAt,emotionCount,excludedCountries,includedCountries,isCommentEnabled,isHiddenFromStar,lastModifierMember,notice,officialVideo,plainBody,postId,postVersion,reservation,starReactions,targetMember,thumbnail,title,url,viewerEmotionId,writtenIn,sharedPosts,originPost{}&sortType=LATEST&limit=100&gcc=KR"

def get_partial_list(afterStr):
    obj = requests.get(all_vlives_endpoint.format(afterStr), headers = headers).json()
    return obj['paging'], obj['data']

links = []
i = 0
while True:
    if i == 0:
        pagingParams, partialData = get_partial_list('')
        links.extend(partialData)
        i += 1
    else:
        pagingParams, partialData = get_partial_list("&after="+pagingParams['nextParams']['after'])
        links.extend(partialData)
        if 'nextParams' not in pagingParams:
            #reached end of list
            break

print('# of videos found: ' + str(len(links)))

for vlive in tqdm(links):
    attempts = 0

    title = vlive['title']
    # kr_title = vlive['officialVideo']['title']

    date = datetime.datetime.utcfromtimestamp(vlive['createdAt']/1000).strftime("%Y%m%d%H%M")

    video_id = str(vlive['officialVideo']['videoSeq'])
    postUrl = vlive['url']
    vodId = vlive['officialVideo']['vodId']

    print(date, video_id, title)

    video_path = "D:/izone/" + date + '_' +video_id 

    naver_link_endpoint = "https://www.vlive.tv/globalv-web/vam-web/video/v1.0/vod/%s/inkey?appId=8c6cc7b45d2568fb668be6e05b6e5a3b&gcc=KR"
    headers = {
        'Referer': postUrl
    }
    naver_link_r = requests.get(naver_link_endpoint % video_id, headers = headers).json()
    #testing purposes
    if not 'inkey' in naver_link_r:
        print(naver_link_r)
    naver_key = naver_link_r['inkey']

    naver_link = "https://apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/%s?key=%s" % (vodId, naver_key)

    video_r = requests.get(naver_link).json()
    video_res = video_r['videos']['list']
    sorted_video_res = sorted(video_res, key = lambda k: k['encodingOption']['height'])
    video_link = sorted_video_res[-1]['source']

    if os.path.exists(video_path):
        for roots, dirs, files in os.walk(video_path):
            if 'captions' in video_r:
                #if the video has captions
                for language in video_r['captions']['list']:
                    code_and_type = language['language'] + '-' + language['type']
                    sub_link = language['source']
                    if not os.path.exists(video_path + '/' + code_and_type + '/'):
                        os.mkdir(video_path + '/' + code_and_type)
                        urllib.request.urlretrieve(sub_link, video_path + '/' + code_and_type + '/' + code_and_type + ".vtt")
                        # sub_r = requests.get(sub_link)
                        # with open(video_path + '/' + code_and_type + '/' + code_and_type + '.vtt', 'wb') as f:
                        #     f.write(sub_r.content)
                        print('Acquired ' + code_and_type + '.vtt')

            if not any('.mp4' in x for x in files):
                #no video
                while attempts < 5:
                    try:
                        urllib.request.urlretrieve(video_link, video_path + '/' + video_id + '.mp4')
                        # vid_r = requests.get(video_link)
                        # with open(video_path + '/' + video_id + '.mp4', 'wb') as f:
                        #     f.write(vid_r.content)
                        print('Acquired ' + video_id + '.mp4')
                        break
                    except:
                        attempts += 1
                        pass

            if not 'title.txt' in files:
                #no title
                with open(video_path + '/' + 'title.txt', 'w', encoding = 'utf-8') as f:
                    f.write(title)
                print('Acquired title.txt')
            
            #top level dir
            break

    else:
        #should only happen when auto_downloaded video is re-checked by no_selenium
        matching_id_dir = [x for x in os.listdir("D:/izone/") if video_id in x.split("_")[1]]
        if len(matching_id_dir) != 0:
            matching_id_date = matching_id_dir[0].split("_")[0]
            if not matching_id_date == date:
                print('SAME VIDEO ID EXISTS, DIFFERENT DATE: ', date, video_id)
                print(matching_id_dir[0])
                #if new time is less than 10 minutes apart from matching id date
                if (datetime.datetime.strptime(date, "%Y%m%d%H%M") - datetime.datetime.strptime(matching_id_date, "%Y%m%d%H%M")).total_seconds() < 600:
                    print('Updating date...')
                    os.rename("D:/izone/"+matching_id_dir[0], "D:/izone/" + date + '_' + video_id)
        else:
            os.mkdir(video_path)

            while attempts < 5:
                try:
                    urllib.request.urlretrieve(video_link, video_path + '/' + video_id+'.mp4')
                    # vid_r = requests.get(video_link)
                    # with open(video_path + '/' + video_id + '.mp4', 'wb') as f:
                    #     f.write(vid_r.content)
                    print('Acquired ' + video_id + '.mp4')
                    break
                except:
                    attempts += 1
                    pass


            if 'captions' in video_r:
                #if video has captions
                for language in video_r['captions']['list']:
                    code_and_type = language['language'] + '-' + language['type']
                    sub_link = language['source']
                    os.mkdir(video_path + '/' + code_and_type)
                    urllib.request.urlretrieve(sub_link, video_path + '/' + code_and_type + '/' + code_and_type + ".vtt")
                    # sub_r = requests.get(sub_link)
                    # with open(video_path + '/' + code_and_type + '/' + code_and_type + '.vtt', 'wb') as f:
                        # f.write(sub_r.content)
                    print('Acquired ' + code_and_type + '.vtt')

            with open(video_path + '/' + 'title.txt', 'w', encoding = 'utf-8') as f:
                f.write(title)
            print('Acquired title.txt')