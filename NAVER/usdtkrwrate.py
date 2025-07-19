import requests

cookies = {
    "NAC": "2QfGCIBudkAvB",
    "NNB": "5VYPEL22ENFGQ",
    "_naver_usersession_": "fo11wAsIguwpgB3NPgxlng==",
    "SRT30": "1752901307",
    "SRT5": "1752901307",
    "page_uid": "jcVFZlqptbNssCq2SA0ssssstmo-042991",
    "BUC": "YxFFeGb7WKKpPsaFnPzdYRByVimsTwvDlcZUcJ5oBKg=",
}

headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
    "content-type": "application/json",
    "origin": "https://m.stock.naver.com",
    "priority": "u=1, i",
    "referer": "https://m.stock.naver.com/crypto/UPBIT/USDT",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    # 'cookie': 'NAC=2QfGCIBudkAvB; NNB=5VYPEL22ENFGQ; _naver_usersession_=fo11wAsIguwpgB3NPgxlng==; SRT30=1752901307; SRT5=1752901307; page_uid=jcVFZlqptbNssCq2SA0ssssstmo-042991; BUC=YxFFeGb7WKKpPsaFnPzdYRByVimsTwvDlcZUcJ5oBKg=',
}

json_data = {
    "fqnfTickers": [
        "USDT_KRW_UPBIT",
        "USDT_KRW_BITHUMB",
    ],
}

response = requests.post(
    "https://m.stock.naver.com/front-api/realTime/crypto",
    cookies=cookies,
    headers=headers,
    json=json_data,
)

# Note: json_data will not be serialized by requests
# exactly as it was in the original request.
# data = '{"fqnfTickers":["USDT_KRW_UPBIT","USDT_KRW_BITHUMB"]}'
# response = requests.post('https://m.stock.naver.com/front-api/realTime/crypto', cookies=cookies, headers=headers, data=data)
