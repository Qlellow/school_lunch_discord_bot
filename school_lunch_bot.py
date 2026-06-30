import os
import datetime
import re

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# ── 설정 ──────────────────────────────────────────────
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
NEIS_KEY = os.environ.get("NEIS_KEY")

ATPT_CODE = "R10"          # 경상북도교육청
SCHOOL_CODE = "8750829"    # 경북소프트웨어마이스터고등학교
SCHOOL_NAME = "경북소프트웨어마이스터고등학교"

NEIS_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

# 끼니 코드 → 이름
MEAL_TYPES = {"1": "조식", "2": "중식", "3": "석식"}
KST = datetime.timezone(datetime.timedelta(hours=9))


# ── NEIS 급식 조회 ────────────────────────────────────
async def fetch_meals(date: datetime.date) -> dict[str, str]:
    """해당 날짜 급식을 {끼니이름: 메뉴} 형태로 반환. 없으면 빈 dict."""
    params = {
        "Type": "json",
        "KEY": NEIS_KEY,
        "ATPT_OFCDC_SC_CODE": ATPT_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MLSV_YMD": date.strftime("%Y%m%d"),
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(NEIS_URL, params=params) as resp:
            data = await resp.json(content_type=None)

    rows = data.get("mealServiceDietInfo")
    if not rows:  # 급식 없는 날 → RESULT 에러만 옴
        return {}

    meals: dict[str, tuple[list[str], str]] = {}
    for row in rows[1]["row"]:
        name = MEAL_TYPES.get(row["MMEAL_SC_CODE"], row["MMEAL_SC_NM"])
        # 알레르기 번호 제거 + <br/> → 줄단위 리스트
        dishes = re.sub(r"\s*\([\d.]+\)", "", row["DDISH_NM"])
        lines = [d.strip() for d in dishes.split("<br/>") if d.strip()]
        cal = row.get("CAL_INFO", "")
        meals[name] = (lines, cal)
    return meals


# 끼니별 헤딩 이모지
# MEAL_EMOJI = {"조식": "🌅", "중식": "🍱", "석식": "🌙"}


def build_embed(date: datetime.date, meals: dict[str, tuple[list[str], str]], label: str = "급식") -> discord.Embed:
    weekday = ["월", "화", "수", "목", "금", "토", "일"][date.weekday()]
    title = f"🍽️ {date.strftime('%Y-%m-%d')} ({weekday}) {label}"
    embed = discord.Embed(title=title, color=0x00A86B)
    embed.set_footer(text=SCHOOL_NAME)

    if not meals:
        embed.description = "급식 정보가 없어요. (주말/공휴일이거나 아직 미등록)"
        return embed

    blocks = []
    for name, (lines, cal) in meals.items():
        # 메뉴는 인용글(>), 흰 글씨로 보이게 굵게
        body = "\n".join(f"> **{d}**" for d in lines)
        if cal:
            body += f"\n`{cal}`"
        blocks.append(body)
    embed.description = "\n\n".join(blocks)
    return embed


# ── 봇 ────────────────────────────────────────────────
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"슬래시 명령 {len(synced)}개 동기화 완료")
    except Exception as e:
        print(f"동기화 실패: {e}")
    print(f"로그인: {bot.user}")


def _parse_date(date_str: str | None) -> datetime.date | None:
    """None/'오늘'/'내일' 또는 YYYY-MM-DD, MMDD 파싱."""
    today = datetime.datetime.now(KST).date()
    if not date_str or date_str in ("오늘", "today"):
        return today
    if date_str in ("내일", "tomorrow"):
        return today + datetime.timedelta(days=1)
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%m-%d", "%m%d"):
        try:
            d = datetime.datetime.strptime(date_str, fmt).date()
            return d.replace(year=today.year) if fmt in ("%m-%d", "%m%d") else d
        except ValueError:
            continue
    return None


@bot.tree.command(name="급식", description="오늘(또는 지정일) 급식을 알려줍니다.")
@app_commands.describe(
    type="끼니 (생략 시 전체)",
    date="오늘/내일 또는 YYYY-MM-DD, MMDD (생략 시 오늘)",
)
@app_commands.choices(
    type=[
        app_commands.Choice(name="조식", value="1"),
        app_commands.Choice(name="중식", value="2"),
        app_commands.Choice(name="석식", value="3"),
    ]
)
async def meal_cmd(
    interaction: discord.Interaction,
    type: app_commands.Choice[str] | None = None,
    date: str | None = None,
):
    target = _parse_date(date)
    if target is None:
        await interaction.response.send_message(
            "날짜 형식이 틀렸어요. 예: `2026-06-30`, `0630`, `내일`", ephemeral=True
        )
        return
    await interaction.response.defer()
    try:
        meals = await fetch_meals(target)
    except Exception as e:
        await interaction.followup.send(f"조회 중 오류: {e}")
        return

    label = "급식"
    if type is not None:  # 특정 끼니만 필터
        wanted = MEAL_TYPES[type.value]
        meals = {wanted: meals[wanted]} if wanted in meals else {}
        label = wanted
    await interaction.followup.send(embed=build_embed(target, meals, label))


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("환경변수 DISCORD_TOKEN 이 필요합니다.")
    if not NEIS_KEY:
        raise SystemExit("환경변수 NEIS_KEY 가 필요합니다. (open.neis.go.kr 발급)")
    bot.run(DISCORD_TOKEN)
