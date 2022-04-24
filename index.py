

##基于统一身份认证的寝室电费查询系统，支持所有校区（只要你该填的不填错）
##该认证方法使用学校所有可以使用统一身份认证登录的网页平台（因为方法都一样虽然没试过/狗头）
##现在默认认证的是在线缴费平台，有其他平台需要自己改。认证都在 loing_authserver_ntu（） 这个函数里面了，返回值是一个带通行证的连接，用对象get一下获取cookie就行(我就这么干的)

#用于get和post请求、json编码、sys控制错误的时候结束程序
import requests,json,sys
#用于执行统一身份认证用来加密明文密码的js脚本
import execjs
#用来进行xpath定位网页的部分内容
from lxml import etree
'''
例：
    reusername="你的学号"
    #统一身份登录的密码
    repassword="你的登录密码"
    #填所在校区。校区的名字可以在下面chooseSchool里看
    youschool="启东校区"
    #填寝室楼名称
    rebuilding="11号楼"
    #填写寝室号通常楼号+寝室门号。充过电费应该都知道是什么意思
    reroom="11103"
    #设定一个电力阈值
    lowpower=30
    #消息推送的密钥 申请地址（http://www.pushplus.plus/）免费的
    pushplus_parameters="上面连接获取到的token"
    #是否一对多推送
    group=False
    #以上为true时必填
    groupid=''
'''
#学工号
reusername=""
#统一身份登录的密码
repassword=""
#填所在校区。校区的名字可以在下面chooseSchool里看
youschool=""
#填寝室楼名称
rebuilding=""
#填写寝室号通常楼号+寝室门号。充过电费应该都知道是什么意思
reroom=""
#设定一个电力阈值
lowpower=30
#消息推送的密钥 申请地址（http://www.pushplus.plus/）免费的
pushplus_parameters=""
#是否一对多推送
group=False
#以上为true时必填
groupid=''

chooseSchool=[                  #不需要修改
              {'school':'启东校区','eletype':'1','sign':'qidong'},
              {'school':'啬园校区','eletype':'2','sign':'zhuxiaoqu'},
              {'school':'钟秀校区','eletype':'3','sign':'zhongxiu'},
              {'school':'启秀校区','eletype':'4','sign':'qixiu'}
]
session2=requests.session()
#建立一个会话对象
def loing_authserver_ntu(reusername,repassword):     #利用统一身份认证，返回票据
    session=requests.session()
    login_url='http://authserver.ntu.edu.cn/authserver/login?service=http://pay.ntu.edu.cn/signAuthentication?url=openUserPayProList'
    #利用get取网页中的stal，lt,execution,
    thpage_text=session.get(login_url).text
    staltree = etree.HTML(thpage_text)
    thstal=staltree.xpath('//*[@id="pwdDefaultEncryptSalt"]/@value')
    thlt=staltree.xpath('//*[@id="casLoginForm"]/input[1]/@value')
    thexecution=staltree.xpath('//*[@id="casLoginForm"]/input[3]/@value')
    encrypt_script_url = 'http://authserver.ntu.edu.cn/authserver/custom/js/encrypt.js'
    js = requests.get(encrypt_script_url).text
    ctx = execjs.compile(js)
    password = ctx.call('_ep', repassword, thstal[0])

    longin_data={
        'username':reusername,
        'password':password,
        'lt':thlt[0],
        'dllt':'userNamePasswordLogin',
        'execution':thexecution[0],
        '_eventId':'submit',
        'rmShown':'1'
    }
    login_res=session.post(login_url,longin_data,allow_redirects=False)
    try:
        backhead=login_res.headers['Location']
    except KeyError:
        print('账号密码错误或需要验证码！')
        sys.exit(0)
    return(backhead)

def find_list(num,content):                              #从列表中找到并返回需要的字典
    if num==1 :
        for i in chooseSchool:
            if i['school']==content:
                return i
    elif num==2:
        for i in content:
            if i['buildingname'] == rebuilding:
                return i
    elif num==3:
        for i in content:
            if i['roomname']==reroom:
                return i['roomid']
    return('x')

def get_buildinglist(schoolcontent):                         #获取该校区的寝室楼列表
    get_bulist_url='http://pay.ntu.edu.cn/querybuildingList'
    if schoolcontent == 'x':
        print('在 南通大学 没有找到这个校区！')
        sys.exit(0)
    list_post_data={
        'eletype':schoolcontent['eletype'],
        'factorycode':'E017',
        'sign':schoolcontent['sign']
    }
    blist=session2.post(get_bulist_url,list_post_data)
    if '系统正在结账' in blist.text:
        print('系统正在结账，无法查询')
        sys.exit(0)
    blistj=json.loads(blist.text).get('buildinglist')
    return(blistj)

def get_roomslist(schoolcontent,buildingcontent):            #获取该寝室楼的房间列表
    get_roomlist_url='http://pay.ntu.edu.cn/queryRoomList'
    if buildingcontent == 'x':
        print(f'在 {youschool} 中没有找到这个寝室楼！')
        sys.exit(0)
    list_post_data={
        'buildingid':buildingcontent['buildingid'],
        'schoolid':schoolcontent['eletype'],
        'factorycode':'E017',
        'sign':schoolcontent['sign']
    }
    rlist=session2.post(get_roomlist_url,list_post_data)
    rlistj=json.loads(rlist.text).get('roomlist')
    return(rlistj)

def get_power(schoolcontent,buildingcontent,roomid):          #取得剩余电力
    POST_url='http://pay.ntu.edu.cn/querySydl'
    if roomid == 'x':
        print(f'在{youschool} {rebuilding} 中没有找到这个寝室号！')
        sys.exit(0)
    requestbody = {
        'room_id':roomid,
        'loudong_id':buildingcontent['buildingid'],
        'xiaoqu_id':schoolcontent['eletype'],
        'factorycode':'E017',
        'sign':schoolcontent['sign']
    }
    res=session2.post(POST_url,data=requestbody)
    ress=res.json()
    return ress['balance']

def sentmsg(surplus_power):                                 #低电量发信
    sentmsg_url='http://www.pushplus.plus/send'
    if group:
        requestbody={
            'token':pushplus_parameters,
            'title':'寝室电力预警',
            'topic':groupid,
            'content':f'{youschool}{reroom}寝室还剩 {surplus_power} 度电,已经低于你设置的 {lowpower} 度电的值'
        }
    else:
        requestbody={
            'token':pushplus_parameters,
            'title':'寝室电力预警',
            'content':f'{youschool}{reroom}寝室还剩 {surplus_power} 度电,已经低于你设置的 {lowpower} 度电的值'
        }
    ressent=requests.post(sentmsg_url,data=requestbody)
    print(json.loads(ressent.text).get('msg'))


def main():
    backhead=loing_authserver_ntu(reusername,repassword)
    #登录获取302的url其中包含通行证
    session2.get(backhead)
    #上面这步get是为了向session对象中添加通过账户验证的cookie
    schoolcontent=find_list(1,youschool)
    buildinglist=get_buildinglist(schoolcontent)
    buildingcontent=find_list(2,buildinglist)
    roomslist=get_roomslist(schoolcontent,buildingcontent)
    roomid=find_list(3,roomslist)
    surplus_power=get_power(schoolcontent,buildingcontent,roomid)
    print(f'{youschool}{reroom}寝室还剩 {surplus_power} 度电')
    if surplus_power < lowpower:
        sentmsg(surplus_power)

if __name__ == '__main__':
    '''本地执行入口'''
    main()

def handler(event, context):
    '''阿里云的入口函数'''
    main()


def main_handler(event, context):
    '''腾讯云的入口函数'''
    main()
    return 'ok'