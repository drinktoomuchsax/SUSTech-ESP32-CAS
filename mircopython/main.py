import network
import urequests
import time
import machine
import ubinascii
import re

# 配置部分
WIFI_SSID = 'SUSTech-wifi'
WIFI_PASSWORD = ''  # 无密码

CAS_LOGIN_URL = 'https://cas.sustech.edu.cn/cas/login?service=http%3A%2F%2F172.16.16.20%3A803%2Fsustc_cas.php'
CAS_POST_URL = 'https://cas.sustech.edu.cn/cas/login?service=http%3A%2F%2F172.16.16.20%3A803%2Fsustc_cas.php'

USERNAME = 'xxx'  # 请替换为你的教/学工号
PASSWORD = 'xxx'  # 请替换为你的密码

# 全局变量来存储 Cookies
cookies = ''


def build_post_data(username, password, execution):
    username_encoded = username.replace('&', '%26').replace('=', '%3D')
    password_encoded = password.replace('&', '%26').replace('=', '%3D')

    execution_encoded = execution

    post_data = (
        f'username={username_encoded}'
        f'&password={password_encoded}'
        f'&execution={execution_encoded}'
        f'&_eventId=submit'
        f'&geolocation='  
    )
    return post_data


# 连接 Wi-Fi
def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('正在连接到 Wi-Fi 网络 "{}"...'.format(ssid))
        wlan.connect(ssid, password)
        timeout = 20  # 连接超时设置为20秒
        start_time = time.time()
        while not wlan.isconnected():
            if time.time() - start_time > timeout:
                print('连接 Wi-Fi 超时，请检查网络设置。')
                return False
            print('.', end='')
            time.sleep(1)
    print('\n已连接到网络')
    print('网络配置:', wlan.ifconfig())
    return True


# 获取 Cookies
def extract_cookies(response):
    global cookies
    print('开始提取 Cookies...')
    set_cookie = response.headers.get('Set-Cookie')
    if set_cookie:
        print('响应头 Set-Cookie:', set_cookie)
        # 处理所有 Set-Cookie（可能有多个）
        if isinstance(set_cookie, list):
            for cookie in set_cookie:
                cookies += cookie.split(';')[0] + '; '
        else:
            cookies += set_cookie.split(';')[0] + '; '
        print('累计的 Cookies:', cookies)
    else:
        print('未获取到 Cookies')


# 执行登录流程
def cas_login():
    try:
        print('发送 GET 请求获取登录页面...')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
                          'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                          'Chrome/85.0.4183.83 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }
        response = urequests.get(CAS_LOGIN_URL, headers=headers)
        print('GET 请求响应状态码:', response.status_code)
        print('GET 请求响应头:', response.headers)
        html = response.text
        print('GET 请求响应内容长度:', len(html))
        extract_cookies(response)
        response.close()

        print('解析 execution token...')
        match = re.search(r'name="execution" value="(.+?)"', html)
        if not match:
            print('未找到 execution token')
            return False
        execution = match.group(1)
        print(f'获取到的 execution token: {execution}')

        post_data = build_post_data(USERNAME, PASSWORD, execution)
        print('POST 数据:', post_data)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
                          'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                          'Chrome/85.0.4183.83 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Referer': CAS_LOGIN_URL,
            'Cookie': cookies  # 添加之前获取的 Cookies
        }

        print('发送 POST 请求进行登录...')
        response = urequests.post(CAS_POST_URL, data=post_data, headers=headers)
        print('POST 请求响应状态码:', response.status_code)
        print('POST 请求响应头:', response.headers)
        post_response_text = response.text
        print('POST 请求响应内容长度:', len(post_response_text))
        print('POST 请求响应内容预览:', post_response_text[:500])  # 仅打印前500字符以避免日志过长
        extract_cookies(response)
        response.close()

        if response.status_code in (301, 302):
            redirect_url = response.headers.get('Location')
            print('服务器返回重定向，重定向到:', redirect_url)
            if redirect_url:
                print('发送 GET 请求到重定向 URL...')
                response_redirect = urequests.get(redirect_url, headers=headers)
                print('重定向 GET 请求响应状态码:', response_redirect.status_code)
                print('重定向 GET 请求响应头:', response_redirect.headers)
                redirect_response_text = response_redirect.text
                print('重定向 GET 请求响应内容长度:', len(redirect_response_text))
                print('重定向 GET 请求响应内容预览:', redirect_response_text[:500])
                extract_cookies(response_redirect)
                response_redirect.close()
                if 'success' in redirect_response_text:
                    print('登录成功（通过重定向检测）')
                    return True
                else:
                    print('重定向后未检测到登录成功的标识')
                    return False
            else:
                print('重定向 URL 不存在')
                return False
        elif response.status_code == 200:
            if 'success' in post_response_text:
                print('登录成功')
                return True
            elif 'failed' in post_response_text:
                print('登录失败：错误提示信息')
                return False
            else:
                print('登录请求已发送，但无法确定是否成功。请手动检查响应内容。')
                return True  # 假设请求已发送
        else:
            print('登录失败，状态码:', response.status_code)
            return False
    except Exception as e:
        print('登录过程中发生错误:', e)
        return False

def main():
    # 连接 Wi-Fi
    if not connect_wifi(WIFI_SSID, WIFI_PASSWORD):
        print('无法连接到 Wi-Fi，程序退出。')
        return

    # 执行 CAS 登录
    if not cas_login():
        print('登录失败，程序退出。')
        return

if __name__ == '__main__':
    main()
