import asyncio
import json
import os
import random

import discord
import team_assignment
from discord import ButtonStyle, Interaction, app_commands
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, View

# Botの初期化
intents = discord.Intents.default()
intents.message_content = True
# intents.guilds = True  # 特権インテント
# intents.members = True  # 特権インテント

bot = commands.Bot(command_prefix="/", intents=intents)

# 参加者リストの一時保存用
entry_data = {}

# データ保存用ディレクトリ
DATA_DIR = './data/player_list'
os.makedirs(DATA_DIR, exist_ok=True)

# --- レート・レーンの選択肢 ---
RANKS = [
    ("Unranked", []),
    ("Iron", ["IV", "III", "II", "I"]),
    ("Bronze", ["IV", "III", "II", "I"]),
    ("Silver", ["IV", "III", "II", "I"]),
    ("Gold", ["IV", "III", "II", "I"]),
    ("Platinum", ["IV", "III", "II", "I"]),
    ("Emerald", ["IV", "III", "II", "I"]),
    ("Diamond", ["IV", "III", "II", "I"]),
    ("Master", []),
    ("GrandMaster", []),
    ("Challenger", [])
]
LANES = ["top", "mid", "jg", "sup", "adc"]

# --- 名前入力モーダル ---


class NameModal(Modal, title="名前入力"):
    def __init__(self, server_id, user_id):
        super().__init__()
        self.server_id = server_id
        self.user_id = user_id
        self.add_item(TextInput(
            label="名前",
            placeholder="あなたの名前を入力してください",
            custom_id="name",
            required=True
        ))

    async def on_submit(self, interaction: Interaction):
        name = self.children[0].value
        # 選択式メッセージを送信
        view = RankSelectView(self.server_id, self.user_id, name)
        await interaction.response.send_message("ランクを選択してください", view=view, ephemeral=True)

# --- ランク選択ビュー ---


class RankSelectView(View):
    def __init__(self, server_id, user_id, name):
        super().__init__()
        self.server_id = server_id
        self.user_id = user_id
        self.name = name

    @discord.ui.select(
        placeholder="ランクを選択",
        options=[discord.SelectOption(label=rank, value=rank)
                 for rank, _ in RANKS]
    )
    async def rank_select(self, interaction: Interaction, select: discord.ui.Select):
        rank = select.values[0]

        # ディビジョンが不要なランクの場合は直接レーン選択へ
        for r, divs in RANKS:
            if r == rank and not divs:
                view = LaneSelectView(
                    self.server_id, self.user_id, self.name, rank, "-")
                await interaction.response.edit_message(content="希望ロールを選択してください", view=view)
                return

        # ディビジョン選択ビューを表示
        view = DivisionSelectView(
            self.server_id, self.user_id, self.name, rank)
        await interaction.response.edit_message(content="ディビジョンを選択してください", view=view)

# --- ディビジョン選択ビュー ---


class DivisionSelectView(View):
    def __init__(self, server_id, user_id, name, rank):
        super().__init__()
        self.server_id = server_id
        self.user_id = user_id
        self.name = name
        self.rank = rank

    @discord.ui.select(
        placeholder="ディビジョンを選択",
        options=[discord.SelectOption(label=div, value=div)
                 for div in ["IV", "III", "II", "I"]]
    )
    async def division_select(self, interaction: Interaction, select: discord.ui.Select):
        division = select.values[0]
        # レーン選択ビューを表示
        view = LaneSelectView(self.server_id, self.user_id,
                              self.name, self.rank, division)
        await interaction.response.edit_message(content="出来ないレーンを選択してください", view=view)

# --- レーン選択ビュー ---


class LaneSelectView(View):
    def __init__(self, server_id, user_id, name, rank, division):
        super().__init__()
        self.server_id = server_id
        self.user_id = user_id
        self.name = name
        self.rank = rank
        self.division = division
        self.selected_lanes = []

        # ALLボタンを追加
        all_button = Button(
            label="ALL",
            style=ButtonStyle.secondary,
            custom_id="lane_all"
        )
        all_button.callback = self.all_button_callback
        self.add_item(all_button)

        # ロール選択ボタンを追加
        for lane in LANES:
            button = Button(
                label=lane.upper(),
                style=ButtonStyle.secondary,
                custom_id=f"lane_{lane}"
            )
            button.callback = self.lane_button_callback
            self.add_item(button)

        # 完了ボタンを追加
        complete_button = Button(
            label="完了",
            style=ButtonStyle.success,
            custom_id="complete"
        )
        complete_button.callback = self.complete_button_callback
        self.add_item(complete_button)

    async def all_button_callback(self, interaction: Interaction):
        if len(self.selected_lanes) == len(LANES):
            # すべて選択されている場合は全解除
            self.selected_lanes = []
            button_style = ButtonStyle.secondary
        else:
            # すべて選択
            self.selected_lanes = LANES.copy()
            button_style = ButtonStyle.primary

        # ボタンのスタイルを更新
        for child in self.children:
            if child.custom_id == "lane_all":
                child.style = button_style
            elif child.custom_id.startswith("lane_"):
                child.style = button_style

        # 選択状態を表示
        status = f"選択中のロール: {', '.join(self.selected_lanes)}" if self.selected_lanes else "ロールを選択してください"
        await interaction.response.edit_message(content=status, view=self)

    async def lane_button_callback(self, interaction: Interaction):
        button = interaction.data["custom_id"]
        lane = button.replace("lane_", "")

        if lane in self.selected_lanes:
            self.selected_lanes.remove(lane)
            button_style = ButtonStyle.secondary
        else:
            self.selected_lanes.append(lane)
            button_style = ButtonStyle.primary

        # ボタンのスタイルを更新
        for child in self.children:
            if child.custom_id == button:
                child.style = button_style
            elif child.custom_id == "lane_all":
                # ALLボタンのスタイルを更新
                child.style = ButtonStyle.primary if len(
                    self.selected_lanes) == len(LANES) else ButtonStyle.secondary

        # 選択状態を表示
        status = f"選択中のロール: {', '.join(self.selected_lanes)}" if self.selected_lanes else "ロールを選択してください"
        await interaction.response.edit_message(content=status, view=self)

    async def complete_button_callback(self, interaction: Interaction):
        if not self.selected_lanes:
            await interaction.response.send_message("少なくとも1つのロールを選択してください。", ephemeral=True)
            return

        # 保存処理
        server_path = os.path.join(DATA_DIR, f"{self.server_id}.json")
        try:
            with open(server_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        data[str(self.user_id)] = {
            "name": self.name,
            "rank": self.rank,
            "division": self.division,
            "lanes": self.selected_lanes
        }

        with open(server_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # メッセージIDからメッセージを取得しEmbedを編集
        try:
            msg_id = int(data.get("_message_id", 0))
            if msg_id:
                channel = interaction.channel
                msg = await channel.fetch_message(msg_id)
                await update_entry_list(msg, self.server_id, data)
        except Exception as e:
            print(f"メッセージ編集失敗: {e}")

        # 完了メッセージを表示（2秒後に自動削除）
        await interaction.response.edit_message(content="エントリー完了しました。", view=None, delete_after=2)

# --- エントリービュー ---


class EntryView(View):
    def __init__(self, server_id):
        super().__init__(timeout=None)
        self.server_id = server_id

    @discord.ui.button(label="エントリー", style=ButtonStyle.primary, custom_id="entry_button")
    async def entry_button(self, interaction: Interaction, button: Button):
        # 名前入力モーダルを表示
        modal = NameModal(server_id=self.server_id,
                          user_id=interaction.user.id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="振り分け開始", style=ButtonStyle.success, custom_id="assign_button")
    async def assign_button(self, interaction: Interaction, button: Button):
        # 参加者データを読み込む
        server_path = os.path.join(DATA_DIR, f"{self.server_id}.json")
        try:
            with open(server_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        # 参加者数をカウント（_message_idを除く）
        player_count = len([k for k in data.keys() if k != "_message_id"])

        if player_count != 10:
            await interaction.response.send_message(
                "参加人数は10人である必要があります。",
                ephemeral=True,
                delete_after=5
            )
            return

        # チーム振り分けを実行
        team_assignment.run(self.server_id)

        # 結果を読み込む
        teams_path = os.path.join("data", "teams", f"{self.server_id}.json")
        try:
            with open(teams_path, "r", encoding="utf-8") as f:
                teams_data = json.load(f)
        except Exception as e:
            print(f"チームデータ読み込みエラー: {e}")
            await interaction.response.send_message(
                "エラーが発生しました。",
                ephemeral=True,
                delete_after=5
            )
            return

        if not teams_data.get("existence", False):
            await interaction.response.send_message(
                "振り分け失敗しました。希望ロールが偏っています。皆さんで話し合い、登録情報を修正してください。修正する対象者は再度エントリーしてください。仲良く話し合いましょう。",
                ephemeral=True,
                delete_after=10
            )
            return

        # ランダムに1つのチーム分けを選択
        team_result = random.choice(teams_data["result"])

        # チーム分け結果をEmbedで表示
        embed = discord.Embed(
            title="チーム振り分け結果",
            color=0x00ff00
        )

        # Team A
        team_a_desc = ""
        for player, info in team_result["team_a"].items():
            team_a_desc += f"・{player} | {info['rank']} | {info['role']} | Score: {info['score']}\n"
        embed.add_field(name="Team A", value=team_a_desc, inline=False)

        # Team B
        team_b_desc = ""
        for player, info in team_result["team_b"].items():
            team_b_desc += f"・{player} | {info['rank']} | {info['role']} | Score: {info['score']}\n"
        embed.add_field(name="Team B", value=team_b_desc, inline=False)

        # スコア差
        embed.add_field(
            name="スコア差",
            value=f"{team_result['difference']}",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

# --- /entryコマンド ---


@bot.tree.command(name="entry", description="エントリーを開始します")
@app_commands.guild_only()
async def entry(interaction: Interaction):
    server_id = str(interaction.guild.id)

    # 既存のデータを読み込む
    server_path = os.path.join(DATA_DIR, f"{server_id}.json")
    try:
        with open(server_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    # 参加者リストのEmbed
    desc = ""
    for user_id, info in data.items():
        if user_id == "_message_id":
            continue
        if isinstance(info, dict):
            rank_display = f"{info['rank']} {info['division']}" if info['division'] != "-" else info['rank']
            desc += f"{info['name']} | {rank_display} | 希望ロール: {', '.join(info['lanes'])}\n"

    if not desc:
        desc = "エントリーした人がここに表示されます。"

    embed = discord.Embed(title="League of Legends カスタム参加者リスト",
                          description=desc, color=0x00ff00)
    view = EntryView(server_id=server_id)
    await interaction.response.send_message(embed=embed, view=view)

    # メッセージIDのみを更新
    sent = await interaction.original_response()
    if "_message_id" in data:
        old_msg_id = data["_message_id"]
        try:
            # 古いメッセージを削除
            channel = interaction.channel
            old_msg = await channel.fetch_message(int(old_msg_id))
            await old_msg.delete()
        except Exception as e:
            print(f"古いメッセージの削除に失敗: {e}")

    data["_message_id"] = str(sent.id)
    with open(server_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 参加者リストEmbedの更新 ---


async def update_entry_list(message, server_id, data=None):
    server_path = os.path.join(DATA_DIR, f"{server_id}.json")

    # データの読み込み
    if data is None:
        try:
            with open(server_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        except json.JSONDecodeError:
            print(f"JSONデコードエラー: {server_path}")
            data = {}

    # 参加者リストの作成
    desc = ""
    for user_id, info in data.items():
        if user_id == "_message_id":
            continue
        if isinstance(info, dict):
            rank_display = f"{info['rank']} {info['division']}" if info['division'] != "-" else info['rank']
            desc += f"{info['name']} | {rank_display} | 希望ロール: {', '.join(info['lanes'])}\n"

    if not desc:
        desc = "エントリーした人がここに表示されます。"

    # Embedの更新
    embed = discord.Embed(title="League of Legends カスタム参加者リスト",
                          description=desc, color=0x00ff00)

    try:
        await message.edit(embed=embed)
    except Exception as e:
        print(f"メッセージ編集失敗: {e}")

# --- /clearコマンド ---


@bot.tree.command(name="clear", description="参加者リストをクリアします")
@app_commands.guild_only()
async def clear(interaction: Interaction):
    server_id = str(interaction.guild.id)
    server_path = os.path.join(DATA_DIR, f"{server_id}.json")

    # JSONファイルを空のデータで上書き
    with open(server_path, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

    # メッセージを更新
    try:
        with open(server_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        msg_id = int(data.get("_message_id", 0))
        if msg_id:
            channel = interaction.channel
            msg = await channel.fetch_message(msg_id)
            await update_entry_list(msg, server_id, {})
    except Exception as e:
        print(f"メッセージ編集失敗: {e}")

    await interaction.response.send_message("参加者リストをクリアしました。", ephemeral=True, delete_after=3)

# --- Bot起動 ---
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # 環境変数から取得、後で設定
    if not TOKEN:
        print("DISCORD_BOT_TOKENを環境変数に設定してください。")
    else:
        @bot.event
        async def on_ready():
            print(f"{bot.user}としてログインしました")

            # グローバルコマンドの同期
            try:
                synced = await bot.tree.sync()
                print(f"スラッシュコマンドを同期しました: {len(synced)}件")
            except Exception as e:
                print(f"グローバルコマンド同期失敗: {e}")

            # ギルドコマンドの同期（テスト用）
            try:
                for guild in bot.guilds:
                    synced = await bot.tree.sync(guild=guild)
                    print(
                        f"ギルド '{guild.name}' のスラッシュコマンドを同期しました: {len(synced)}件")
            except Exception as e:
                print(f"ギルドコマンド同期失敗: {e}")

        bot.run(TOKEN)
