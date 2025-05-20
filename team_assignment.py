import json
import os
from itertools import combinations, permutations

ROLES = ["top", "jg", "mid", "adc", "sup"]


def get_rank_score(rank, division):
    score_table = {
        "unranked": {"-": 1000},
        "iron": {"IV": 1200, "III": 1400, "II": 1600, "I": 1800},
        "bronze": {"IV": 2000, "III": 2200, "II": 2400, "I": 2600},
        "silver": {"IV": 2800, "III": 3000, "II": 3200, "I": 3400},
        "gold": {"IV": 3600, "III": 3800, "II": 4000, "I": 5000},
        "platinum": {"IV": 5200, "III": 5400, "II": 5600, "I": 5800},
        "emerald": {"IV": 6000, "III": 6200, "II": 6400, "I": 6600},
        "diamond": {"IV": 6800, "III": 7000, "II": 7200, "I": 8200},
        "master": {"-": 8400},
        "grandmaster": {"-": 8600},
        "challenger": {"-": 9000}
    }

    return score_table.get(rank.lower(), {}).get(division, 1000)


def load_player_data(server_id):
    file_path = f"./data/player_list/{server_id}.json"

    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        players = {}
        for player_id, player_data in raw_data.items():
            if player_id == "_message_id":
                continue

            name = player_data.get("name", "")
            rank = player_data.get("rank", "unranked")
            division = player_data.get("division", "-")
            lanes = set(player_data.get("lanes", []))

            score = get_rank_score(rank, division)

            players[name] = {
                "rank": rank.lower(),
                "division": division,
                "score": score,
                "role": lanes
            }

        return players

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return {}


def team_combination(players):
    # 全プレイヤー名
    player_names = list(players.keys())
    # チームAの全組み合わせ（5人ずつ）
    team_a_combinations = list(combinations(player_names, 5))
    # 重複チェック用
    seen = set()
    results = []
    # 組み合わせ生成
    for team_a in team_a_combinations:
        team_b = tuple(sorted(set(player_names) - set(team_a)))
        sorted_team_a = tuple(sorted(team_a))
        if sorted_team_a in seen:
            continue
        seen.add(sorted_team_a)
        seen.add(team_b)
        total_a = sum(players[p]["score"] for p in team_a)
        total_b = sum(players[p]["score"] for p in team_b)
        result_team_a = {}
        result_team_b = {}
        for p in list(team_a):
            result_team_a[p] = {
                "score": players[p]["score"],
                "role": None  # ロール情報を初期化
            }
            if players[p]["division"] == "-":
                result_team_a[p]["rank"] = players[p]["rank"]
                continue
            result_team_a[p]["rank"] = players[p]["rank"] + \
                players[p]["division"]
        for p in list(team_b):
            result_team_b[p] = {
                "score": players[p]["score"],
                "role": None  # ロール情報を初期化
            }
            if players[p]["division"] == "-":
                result_team_b[p]["rank"] = players[p]["rank"]
                continue
            result_team_b[p]["rank"] = players[p]["rank"] + \
                players[p]["division"]
        results.append({
            "team_a": result_team_a,
            "team_b": result_team_b,
            "total_a": total_a,
            "total_b": total_b,
            "difference": abs(total_a - total_b)
        })
    return results


def is_team_possible(results, players):
    # 2チームの5人に5ロールのすべての並べ方をチェック
    for result_index, result in enumerate(results):
        results[result_index]["result"] = "NG"
        for role_assignment in permutations(ROLES):
            possible = True
            team_a_players = [a_p for a_p in result["team_a"]]

            # チームAのロール割り当てをチェック
            for player_index, assigned_role in enumerate(role_assignment):
                if assigned_role not in players[team_a_players[player_index]]["role"]:
                    possible = False
                    break

            if not possible:
                continue

            # チームBのロール割り当てをチェック
            for role_assignment_b in permutations(ROLES):
                possible_b = True
                team_b_players = [b_p for b_p in result["team_b"]]

                for player_b_index, assigned_role_b in enumerate(role_assignment_b):
                    if assigned_role_b not in players[team_b_players[player_b_index]]["role"]:
                        possible_b = False
                        break

                if possible_b:
                    # 両チームのロール割り当てが成功した場合、ロールを設定
                    for player_index, assigned_role in enumerate(role_assignment):
                        results[result_index]["team_a"][team_a_players[player_index]
                                                        ]["role"] = assigned_role

                    for player_b_index, assigned_role_b in enumerate(role_assignment_b):
                        results[result_index]["team_b"][team_b_players[player_b_index]
                                                        ]["role"] = assigned_role_b

                    results[result_index]["result"] = "OK"
                    break

            if results[result_index]["result"] == "OK":
                break

    return [result for result in results if result["result"] == "OK"]


def filtered_team(possible_results):
    # difference <= 5000 のデータを抽出
    filtered_results = [
        item for item in possible_results if item['difference'] <= 5000 and item["result"] == "OK"]
    output = {"existence": True}

    # 出力条件の適用
    if len(filtered_results) >= 10:
        output["result"] = sorted(
            filtered_results, key=lambda x: x['difference'])[:10]
    elif len(filtered_results) == 0:
        if len(possible_results) >= 10:
            output["result"] = sorted(
                possible_results, key=lambda x: x['difference'])[:10]
        elif len(possible_results) == 0:
            output["existence"] = False
            output["result"] = []  # 空の結果リストを追加
        else:
            output["result"] = sorted(
                possible_results, key=lambda x: x['difference'])
    else:
        output["result"] = sorted(
            filtered_results, key=lambda x: x['difference'])

    return output


def run(server_id):
    players = load_player_data(server_id)
    teams = team_combination(players)
    possible_teams = is_team_possible(teams, players)
    filtered_teams = filtered_team(possible_teams)
    # JSONファイルとして保存
    with open(f"data/teams/{server_id}.json", "w", encoding="utf-8") as f:
        json.dump(filtered_teams, f, ensure_ascii=False, indent=2)
