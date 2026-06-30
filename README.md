# 급식봇 (경북소프트웨어마이스터고등학교)

NEIS 급식식단정보 API로 우리 학교 급식을 알려주는 디스코드 봇.

## 설치

```bash
pip install -r requirements.txt
```

## 실행

환경변수로 디스코드 봇 토큰을 넣고 실행:

```powershell
$env:DISCORD_TOKEN = "여기에_봇_토큰"
python school_lunch_bot.py
```

(NEIS 키는 코드에 기본값으로 들어가 있음. 바꾸려면 `$env:NEIS_KEY` 설정.)

## 디스코드 봇 토큰 발급

1. https://discord.com/developers/applications → New Application
2. Bot 탭 → Reset Token → 토큰 복사
3. OAuth2 → URL Generator → scope `bot` + `applications.commands` 체크 → 권한 `Send Messages` → 생성된 URL로 서버에 초대

## 사용

슬래시 명령 `/급식`:
- `/급식` → 오늘 급식
- `/급식 날짜:내일`
- `/급식 날짜:2026-06-30` 또는 `/급식 날짜:0630`

조식·중식·석식 + 칼로리 표시. (알레르기 번호는 제거함)
# school_lunch_discord_bot
