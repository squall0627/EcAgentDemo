import csv
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict
import os

from db.database import SessionLocal, init_db
from db.models.product import Product
from db.models.order import Order, OrderItem


class TestDataGenerator:
    """テストデータ生成クラス"""

    def __init__(self):
        """初期化"""
        self.products_data = []
        self.orders_data = []
        self.order_items_data = []

        # 商品カテゴリの定義（日本語）
        self.categories = [
            "食品・飲料", "日用品・雑貨", "家電・デジタル", "ファッション・アパレル",
            "美容・コスメ", "本・雑誌", "スポーツ・アウトドア", "おもちゃ・ゲーム",
            "ペット用品", "医薬品・健康", "インテリア・家具", "キッチン用品",
            "文房具・オフィス用品", "自動車用品", "園芸・DIY"
        ]

        # 注文ステータスの定義
        self.order_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
        self.payment_statuses = ['unpaid', 'paid', 'refunded', 'partial_refund']
        self.shipping_statuses = ['not_shipped', 'preparing', 'shipped', 'in_transit', 'delivered']

        # 日本の都道府県リスト
        self.prefectures = [
            "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]

    def generate_jancode(self) -> str:
        """JANコードを生成"""
        return f"49{random.randint(10000000000, 99999999999)}"

    def generate_product_name(self, category: str) -> Dict[str, str]:
        """カテゴリに応じた商品名を生成（重複を避けるため豊富なバリエーション）"""
        product_names = {
            "食品・飲料": [
                "有機野菜ジュース", "プレミアム醤油", "手作りパン", "特選お米", "冷凍餃子", "インスタントラーメン", 
                "緑茶ティーバッグ", "コーヒー豆", "オリーブオイル", "蜂蜜", "チーズ", "ヨーグルト", "牛乳", 
                "卵", "バター", "パスタ", "トマトソース", "カレールー", "味噌", "みりん", "酢", "砂糖", 
                "塩", "胡椒", "スパイス", "ハーブ", "紅茶", "ウーロン茶", "ほうじ茶", "抹茶", "ココア", 
                "ジュース", "炭酸水", "ミネラルウォーター", "エナジードリンク", "プロテイン", "サプリメント",
                "クッキー", "チョコレート", "キャンディ", "グミ", "せんべい", "ポテトチップス", "ナッツ"
            ],
            "日用品・雑貨": [
                "洗濯洗剤", "ティッシュペーパー", "歯ブラシセット", "シャンプー", "タオルセット", "石鹸", 
                "掃除用品", "キッチンペーパー", "トイレットペーパー", "洗顔料", "ボディソープ", "リンス", 
                "歯磨き粉", "マウスウォッシュ", "デオドラント", "ハンドクリーム", "ボディクリーム", 
                "洗濯ネット", "ハンガー", "洗濯バサミ", "スポンジ", "たわし", "ゴム手袋", "マスク", 
                "絆創膏", "綿棒", "コットン", "爪切り", "毛抜き", "櫛", "ブラシ", "鏡", "懐中電灯", 
                "電池", "延長コード", "電球", "蚊取り線香", "殺虫剤", "芳香剤", "除湿剤", "カイロ"
            ],
            "家電・デジタル": [
                "スマートフォン", "ノートパソコン", "電子レンジ", "掃除機", "炊飯器", "エアコン", "テレビ", 
                "冷蔵庫", "洗濯機", "食器洗い機", "オーブン", "トースター", "コーヒーメーカー", "ミキサー", 
                "ジューサー", "ホットプレート", "IHクッキングヒーター", "電気ケトル", "電気ポット", 
                "ドライヤー", "ヘアアイロン", "電気シェーバー", "マッサージ器", "空気清浄機", "加湿器", 
                "除湿機", "扇風機", "ヒーター", "こたつ", "電気毛布", "アイロン", "ミシン", "プリンター", 
                "スキャナー", "Webカメラ", "スピーカー", "イヤホン", "ヘッドホン", "充電器", "モバイルバッテリー"
            ],
            "ファッション・アパレル": [
                "Tシャツ", "ジーンズ", "スニーカー", "ワンピース", "コート", "帽子", "バッグ", "腕時計", 
                "シャツ", "ブラウス", "スカート", "パンツ", "ジャケット", "セーター", "カーディガン", 
                "パーカー", "トレーナー", "ポロシャツ", "タンクトップ", "キャミソール", "下着", "靴下", 
                "ストッキング", "タイツ", "手袋", "マフラー", "ストール", "ベルト", "ネクタイ", "蝶ネクタイ", 
                "サングラス", "眼鏡", "財布", "名刺入れ", "キーケース", "ハンカチ", "傘", "レインコート", 
                "水着", "パジャマ", "ルームウェア", "エプロン", "作業着", "制服"
            ],
            "美容・コスメ": [
                "化粧水", "美容液", "ファンデーション", "口紅", "アイシャドウ", "マスカラ", "クレンジング", 
                "日焼け止め", "乳液", "クリーム", "パック", "洗顔フォーム", "化粧下地", "コンシーラー", 
                "チーク", "アイライナー", "眉ペンシル", "リップグロス", "リップクリーム", "ネイル", 
                "除光液", "香水", "オードトワレ", "ボディミスト", "入浴剤", "ボディスクラブ", "ヘアワックス", 
                "ヘアスプレー", "ヘアオイル", "ヘアマスク", "白髪染め", "育毛剤", "まつげ美容液", 
                "アイクリーム", "リップ美容液", "ハンドパック", "フットクリーム", "角質ケア", "毛穴パック"
            ],
            "本・雑誌": [
                "小説", "漫画", "雑誌", "参考書", "辞書", "図鑑", "写真集", "画集", "料理本", "旅行ガイド", 
                "ビジネス書", "自己啓発書", "歴史書", "科学書", "医学書", "法律書", "経済書", "哲学書", 
                "宗教書", "芸術書", "音楽書", "スポーツ書", "健康書", "育児書", "教育書", "語学書", 
                "コンピュータ書", "技術書", "工学書", "建築書", "デザイン書", "ファッション誌", "グルメ誌", 
                "趣味雑誌", "週刊誌", "月刊誌", "季刊誌", "年鑑", "カタログ", "パンフレット"
            ],
            "スポーツ・アウトドア": [
                "ランニングシューズ", "トレーニングウェア", "ヨガマット", "ダンベル", "バーベル", "トレーニングベンチ", 
                "エクササイズバイク", "ランニングマシン", "プロテイン", "サプリメント", "水筒", "タオル", 
                "テント", "寝袋", "マット", "バックパック", "登山靴", "トレッキングポール", "コンパス", 
                "懐中電灯", "ランタン", "バーナー", "クッカー", "食器", "カトラリー", "クーラーボックス", 
                "釣り竿", "リール", "ルアー", "餌", "クーラーボックス", "折りたたみ椅子", "テーブル", 
                "タープ", "ハンモック", "双眼鏡", "カメラ", "三脚", "防水ケース", "救急セット"
            ],
            "おもちゃ・ゲーム": [
                "ぬいぐるみ", "人形", "ミニカー", "プラモデル", "パズル", "ブロック", "積み木", "楽器", 
                "ボール", "フリスビー", "縄跳び", "けん玉", "コマ", "ヨーヨー", "シャボン玉", "水鉄砲", 
                "砂場セット", "お絵かきセット", "粘土", "折り紙", "シール", "カード", "ボードゲーム", 
                "テレビゲーム", "携帯ゲーム", "ゲームソフト", "コントローラー", "ヘッドセット", "充電器", 
                "メモリーカード", "ケース", "スタンド", "クリーナー", "保護フィルム", "アクセサリー", 
                "フィギュア", "トレーディングカード", "ステッカー", "バッジ", "キーホルダー"
            ],
            "ペット用品": [
                "ドッグフード", "キャットフード", "おやつ", "水入れ", "餌入れ", "首輪", "リード", "ハーネス", 
                "ケージ", "キャリーバッグ", "ベッド", "クッション", "毛布", "タオル", "トイレ", "トイレシート", 
                "猫砂", "消臭剤", "シャンプー", "ブラシ", "爪切り", "歯ブラシ", "歯磨き粉", "耳掃除", 
                "目薬", "サプリメント", "薬", "包帯", "体温計", "おもちゃ", "ボール", "ロープ", "ぬいぐるみ", 
                "猫じゃらし", "爪とぎ", "キャットタワー", "ドッグハウス", "サークル", "ゲート", "階段", 
                "スロープ", "カート", "バギー", "レインコート", "靴", "靴下", "服"
            ],
            "医薬品・健康": [
                "風邪薬", "解熱剤", "鎮痛剤", "胃腸薬", "便秘薬", "下痢止め", "咳止め", "のど飴", "目薬", 
                "点鼻薬", "湿布", "軟膏", "絆創膏", "包帯", "ガーゼ", "消毒液", "体温計", "血圧計", 
                "血糖値測定器", "マスク", "手袋", "アルコール", "うがい薬", "ビタミン", "ミネラル", 
                "プロテイン", "コラーゲン", "グルコサミン", "コンドロイチン", "DHA", "EPA", "乳酸菌", 
                "酵素", "青汁", "黒酢", "にんにく", "しじみ", "ウコン", "高麗人参", "プロポリス", 
                "ローヤルゼリー", "マヌカハニー", "アロエ", "クロレラ", "スピルリナ"
            ],
            "インテリア・家具": [
                "ソファ", "テーブル", "椅子", "ベッド", "マットレス", "枕", "布団", "シーツ", "カーテン", 
                "ブラインド", "ラグ", "カーペット", "クッション", "照明", "ランプ", "時計", "鏡", "絵画", 
                "写真立て", "花瓶", "観葉植物", "造花", "キャンドル", "アロマ", "収納ボックス", "本棚", 
                "タンス", "クローゼット", "ハンガーラック", "靴箱", "傘立て", "ゴミ箱", "灰皿", "コースター", 
                "ティッシュケース", "リモコンスタンド", "小物入れ", "トレー", "バスケット", "フック", 
                "突っ張り棒", "すのこ", "パーテーション", "スクリーン", "マット"
            ],
            "キッチン用品": [
                "包丁", "まな板", "フライパン", "鍋", "やかん", "ボウル", "ザル", "おたま", "フライ返し", 
                "菜箸", "計量カップ", "計量スプーン", "キッチンスケール", "タイマー", "温度計", "皿", 
                "茶碗", "汁椀", "湯呑み", "マグカップ", "グラス", "箸", "スプーン", "フォーク", "ナイフ", 
                "弁当箱", "水筒", "保温ポット", "急須", "ティーポット", "コーヒーカップ", "ワイングラス", 
                "ビールジョッキ", "徳利", "おちょこ", "重箱", "お盆", "ランチョンマット", "コースター", 
                "ナプキン", "キッチンペーパー", "アルミホイル", "ラップ", "保存容器", "密閉容器"
            ],
            "文房具・オフィス用品": [
                "ペン", "鉛筆", "シャープペンシル", "消しゴム", "定規", "コンパス", "分度器", "はさみ", 
                "カッター", "のり", "テープ", "ホッチキス", "クリップ", "付箋", "ノート", "手帳", 
                "ファイル", "バインダー", "クリアファイル", "封筒", "便箋", "はがき", "切手", "印鑑", 
                "朱肉", "スタンプ", "電卓", "ラベル", "マーカー", "蛍光ペン", "修正液", "修正テープ", 
                "穴あけパンチ", "シュレッダー", "ラミネーター", "プリンター", "コピー用紙", "インク", 
                "トナー", "デスクマット", "ペン立て", "書類トレー", "デスクライト"
            ],
            "自動車用品": [
                "タイヤ", "ホイール", "バッテリー", "オイル", "ワイパー", "ライト", "ミラー", "シート", 
                "ハンドルカバー", "フロアマット", "サンシェード", "カーテン", "芳香剤", "消臭剤", 
                "掃除用品", "洗車用品", "ワックス", "コーティング剤", "タイヤチェーン", "スタッドレスタイヤ", 
                "ジャッキ", "工具", "ブースターケーブル", "三角表示板", "発煙筒", "救急セット", 
                "ドライブレコーダー", "カーナビ", "ETC", "レーダー探知機", "カーオーディオ", "スピーカー", 
                "アンプ", "ウーファー", "充電器", "インバーター", "シガーソケット", "USBポート", 
                "スマホホルダー", "ドリンクホルダー", "ティッシュケース", "ゴミ箱"
            ],
            "園芸・DIY": [
                "種", "苗", "球根", "肥料", "土", "鉢", "プランター", "じょうろ", "スコップ", "熊手", 
                "剪定ばさみ", "軍手", "エプロン", "帽子", "長靴", "ホース", "スプリンクラー", "支柱", 
                "ネット", "防虫剤", "除草剤", "殺菌剤", "温室", "ビニールハウス", "工具", "ドライバー", 
                "ハンマー", "のこぎり", "やすり", "ペンチ", "スパナ", "レンチ", "ドリル", "ビット", 
                "ネジ", "釘", "ボルト", "ナット", "ワッシャー", "接着剤", "シーリング材", "塗料", 
                "刷毛", "ローラー", "マスキングテープ", "サンドペーパー", "メジャー", "水準器", "安全用品"
            ]
        }

        base_names = product_names.get(category, ["汎用商品"])
        base_name = random.choice(base_names)

        # より豊富なバリエーションを追加
        prefixes = ["", "プレミアム", "エコ", "限定版", "新商品", "人気", "おすすめ", "高級", "業務用", 
                   "家庭用", "プロ仕様", "スタンダード", "ベーシック", "アドバンス", "デラックス", "スペシャル"]
        suffixes = ["", "セット", "パック", "ボックス", "キット", "コレクション", "シリーズ", "タイプ", 
                   "モデル", "バージョン", "エディション", "スタイル", "デザイン", "カラー", "サイズ"]

        prefix = random.choice(prefixes)
        suffix = random.choice(suffixes)

        # 商品名を組み立て（重複を避けるためランダム要素を追加）
        if prefix and suffix:
            jp_name = f"{prefix}{base_name}{suffix}"
        elif prefix:
            jp_name = f"{prefix}{base_name}"
        elif suffix:
            jp_name = f"{base_name}{suffix}"
        else:
            jp_name = base_name

        # さらに重複を避けるため、番号やアルファベットを追加する場合がある
        if random.random() < 0.3:  # 30%の確率で追加要素
            extra_elements = [f"#{random.randint(1, 999)}", f"Type-{random.choice('ABCDEFGHIJK')}", 
                            f"Ver.{random.randint(1, 9)}", f"Mark-{random.randint(1, 20)}"]
            jp_name += random.choice(extra_elements)

        return {
            "name_jp": jp_name,
            "name_en": f"Product {random.randint(1000, 9999)}",
            "name_zh": f"产品 {random.randint(1000, 9999)}"
        }

    def generate_products(self, count: int = 300) -> List[Dict]:
        """商品データを生成"""
        print(f"商品データを{count}件生成中...")

        for i in range(count):
            category = random.choice(self.categories)
            names = self.generate_product_name(category)

            # より多様な商品説明を生成
            description_templates = [
                f"{names['name_jp']}は高品質で信頼性の高い商品です。",
                f"{names['name_jp']}をお求めやすい価格でご提供いたします。",
                f"人気の{names['name_jp']}が新登場。お見逃しなく！",
                f"{names['name_jp']}は機能性とデザインを兼ね備えた逸品です。",
                f"厳選された{names['name_jp']}をお届けします。",
                f"{names['name_jp']}で快適な生活をお楽しみください。",
                f"プロも認める{names['name_jp']}の品質をご体験ください。",
                f"{names['name_jp']}は環境に優しい素材を使用しています。",
                f"限定数量の{names['name_jp']}をお早めにどうぞ。",
                f"{names['name_jp']}で毎日をもっと豊かに。",
                f"こだわりの{names['name_jp']}が特別価格で登場。",
                f"{names['name_jp']}は使いやすさを追求した設計です。",
                f"安心・安全な{names['name_jp']}をお選びください。",
                f"{names['name_jp']}で新しいライフスタイルを始めませんか。",
                f"多機能な{names['name_jp']}が日常をサポートします。"
            ]

            product = {
                "jancode": self.generate_jancode(),
                "name_zh": names["name_zh"],
                "name_en": names["name_en"],
                "name_jp": names["name_jp"],
                "category": category,
                "status": random.choice(["published", "unpublished"]),
                "stock": random.randint(0, 1000),
                "price": round(random.uniform(100, 50000), 2),
                "description": random.choice(description_templates)
            }

            self.products_data.append(product)

        print(f"商品データ生成完了: {len(self.products_data)}件")
        return self.products_data

    def generate_customer_info(self) -> Dict[str, str]:
        """顧客情報を生成（メールアドレスはローマ字表記）"""
        # 日本の姓とそのローマ字表記
        surnames_data = [
            ("田中", "tanaka"), ("佐藤", "sato"), ("鈴木", "suzuki"), ("高橋", "takahashi"), 
            ("渡辺", "watanabe"), ("伊藤", "ito"), ("山本", "yamamoto"), ("中村", "nakamura"), 
            ("小林", "kobayashi"), ("加藤", "kato"), ("吉田", "yoshida"), ("山田", "yamada"),
            ("佐々木", "sasaki"), ("山口", "yamaguchi"), ("松本", "matsumoto"), ("井上", "inoue"),
            ("木村", "kimura"), ("林", "hayashi"), ("斎藤", "saito"), ("清水", "shimizu")
        ]

        # 日本の名前とそのローマ字表記
        given_names_data = [
            ("太郎", "taro"), ("花子", "hanako"), ("次郎", "jiro"), ("美咲", "misaki"), 
            ("健太", "kenta"), ("由美", "yumi"), ("翔太", "shota"), ("愛子", "aiko"), 
            ("大輔", "daisuke"), ("恵子", "keiko"), ("雄一", "yuichi"), ("真理", "mari"),
            ("和也", "kazuya"), ("直子", "naoko"), ("博", "hiroshi"), ("美穂", "miho"),
            ("隆", "takashi"), ("智子", "tomoko"), ("修", "osamu"), ("裕子", "yuko")
        ]

        surname_jp, surname_romaji = random.choice(surnames_data)
        given_name_jp, given_name_romaji = random.choice(given_names_data)
        name = f"{surname_jp} {given_name_jp}"

        return {
            "customer_name": name,
            "customer_email": f"{surname_romaji}.{given_name_romaji}@example.com",
            "customer_phone": f"0{random.randint(10, 99)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
        }

    def generate_address(self) -> str:
        """住所を生成"""
        prefecture = random.choice(self.prefectures)
        city = f"{random.choice(['中央', '北', '南', '東', '西'])}区"
        street = f"{random.randint(1, 9)}-{random.randint(1, 20)}-{random.randint(1, 30)}"

        return f"{prefecture}{city}{street}"

    def generate_orders(self, count: int = 300) -> List[Dict]:
        """注文データを生成"""
        print(f"注文データを{count}件生成中...")

        for i in range(count):
            customer_info = self.generate_customer_info()
            order_date = datetime.now() - timedelta(days=random.randint(0, 365))

            order = {
                "order_id": f"ORD{str(uuid.uuid4()).replace('-', '')[:12].upper()}",
                "customer_id": f"CUST{random.randint(100000, 999999)}",
                "customer_name": customer_info["customer_name"],
                "customer_email": customer_info["customer_email"],
                "customer_phone": customer_info["customer_phone"],
                "order_status": random.choice(self.order_statuses),
                "payment_status": random.choice(self.payment_statuses),
                "shipping_status": random.choice(self.shipping_statuses),
                "total_amount": 0,  # 後で計算
                "tax_amount": 0,    # 後で計算
                "shipping_fee": random.choice([0, 500, 800, 1000]),
                "shipping_address": self.generate_address(),
                "billing_address": self.generate_address(),
                "order_date": order_date.isoformat(),
                "shipped_date": (order_date + timedelta(days=random.randint(1, 7))).isoformat() if random.choice([True, False]) else None,
                "delivered_date": (order_date + timedelta(days=random.randint(3, 14))).isoformat() if random.choice([True, False]) else None,
                "notes": random.choice(["", "お急ぎ便希望", "時間指定配送", "ギフト包装希望", "不在時は宅配ボックスへ"]),
                "tracking_number": f"TRK{random.randint(100000000000, 999999999999)}" if random.choice([True, False]) else None
            }

            self.orders_data.append(order)

        print(f"注文データ生成完了: {len(self.orders_data)}件")
        return self.orders_data

    def generate_order_items(self) -> List[Dict]:
        """注文アイテムデータを生成"""
        print("注文アイテムデータを生成中...")

        if not self.products_data or not self.orders_data:
            raise ValueError("商品データと注文データが必要です")

        for order in self.orders_data:
            # 各注文に1〜5個のアイテムをランダムに追加
            num_items = random.randint(1, 5)
            selected_products = random.sample(self.products_data, min(num_items, len(self.products_data)))

            order_total = 0

            for product in selected_products:
                quantity = random.randint(1, 3)
                unit_price = float(product["price"])
                total_price = unit_price * quantity
                order_total += total_price

                order_item = {
                    "order_id": order["order_id"],
                    "jancode": product["jancode"],
                    "product_name": product["name_jp"],
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price
                }

                self.order_items_data.append(order_item)

            # 注文の合計金額を更新
            tax_amount = order_total * 0.1  # 10%の税金
            order["total_amount"] = round(order_total + tax_amount + order["shipping_fee"], 2)
            order["tax_amount"] = round(tax_amount, 2)

        print(f"注文アイテムデータ生成完了: {len(self.order_items_data)}件")
        return self.order_items_data

    def save_to_csv(self, data: List[Dict], filename: str):
        """データをCSVファイルに保存"""
        if not data:
            print(f"警告: {filename}に保存するデータがありません")
            return

        # CSVディレクトリを作成
        os.makedirs("test/csv_data", exist_ok=True)
        filepath = os.path.join("test/csv_data", filename)

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            if data:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

        print(f"CSVファイルに保存完了: {filepath} ({len(data)}件)")

    def generate_all_test_data(self):
        """すべてのテストデータを生成してCSVに保存"""
        print("=== テストデータ生成開始 ===")

        # 商品データ生成
        self.generate_products(300)
        self.save_to_csv(self.products_data, "products.csv")

        # 注文データ生成
        self.generate_orders(300)
        self.save_to_csv(self.orders_data, "orders.csv")

        # 注文アイテムデータ生成
        self.generate_order_items()
        self.save_to_csv(self.order_items_data, "order_items.csv")

        print("=== テストデータ生成完了 ===")


class CSVDataImporter:
    """CSVデータをデータベースにインポートするクラス"""

    def __init__(self):
        """初期化"""
        self.db = SessionLocal()

    def __del__(self):
        """デストラクタ"""
        if hasattr(self, 'db'):
            self.db.close()

    def import_products_from_csv(self, csv_path: str = "test/csv_data/products.csv"):
        """商品データをCSVからインポート"""
        print(f"商品データをインポート中: {csv_path}")

        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                count = 0

                for row in reader:
                    product = Product(
                        jancode=row['jancode'],
                        name_zh=row['name_zh'],
                        name_en=row['name_en'],
                        name_jp=row['name_jp'],
                        category=row['category'],
                        status=row['status'],
                        stock=int(row['stock']),
                        price=Decimal(row['price']),
                        description=row['description']
                    )

                    self.db.add(product)
                    count += 1

                self.db.commit()
                print(f"商品データインポート完了: {count}件")

        except Exception as e:
            self.db.rollback()
            print(f"商品データインポートエラー: {e}")

    def import_orders_from_csv(self, csv_path: str = "test/csv_data/orders.csv"):
        """注文データをCSVからインポート"""
        print(f"注文データをインポート中: {csv_path}")

        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                count = 0

                for row in reader:
                    order = Order(
                        order_id=row['order_id'],
                        customer_id=row['customer_id'],
                        customer_name=row['customer_name'],
                        customer_email=row['customer_email'],
                        customer_phone=row['customer_phone'],
                        order_status=row['order_status'],
                        payment_status=row['payment_status'],
                        shipping_status=row['shipping_status'],
                        total_amount=Decimal(row['total_amount']),
                        tax_amount=Decimal(row['tax_amount']),
                        shipping_fee=Decimal(row['shipping_fee']),
                        shipping_address=row['shipping_address'],
                        billing_address=row['billing_address'],
                        order_date=datetime.fromisoformat(row['order_date']),
                        shipped_date=datetime.fromisoformat(row['shipped_date']) if row['shipped_date'] else None,
                        delivered_date=datetime.fromisoformat(row['delivered_date']) if row['delivered_date'] else None,
                        notes=row['notes'] if row['notes'] else None,
                        tracking_number=row['tracking_number'] if row['tracking_number'] else None
                    )

                    self.db.add(order)
                    count += 1

                self.db.commit()
                print(f"注文データインポート完了: {count}件")

        except Exception as e:
            self.db.rollback()
            print(f"注文データインポートエラー: {e}")

    def import_order_items_from_csv(self, csv_path: str = "test/csv_data/order_items.csv"):
        """注文アイテムデータをCSVからインポート"""
        print(f"注文アイテムデータをインポート中: {csv_path}")

        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                count = 0

                for row in reader:
                    order_item = OrderItem(
                        order_id=row['order_id'],
                        jancode=row['jancode'],
                        product_name=row['product_name'],
                        quantity=int(row['quantity']),
                        unit_price=Decimal(row['unit_price']),
                        total_price=Decimal(row['total_price'])
                    )

                    self.db.add(order_item)
                    count += 1

                self.db.commit()
                print(f"注文アイテムデータインポート完了: {count}件")

        except Exception as e:
            self.db.rollback()
            print(f"注文アイテムデータインポートエラー: {e}")

    def import_all_from_csv(self):
        """すべてのCSVデータをインポート（既存データを削除してから実行）"""
        print("=== CSVデータインポート開始 ===")

        # 既存データをすべて削除
        self.clear_all_data()

        # 順序を守ってインポート（外部キー制約のため）
        self.import_products_from_csv()
        self.import_orders_from_csv()
        self.import_order_items_from_csv()

        print("=== CSVデータインポート完了 ===")

    def clear_all_data(self):
        """すべてのテーブルデータをクリア"""
        print("データベースをクリア中...")

        try:
            # 外部キー制約を考慮して逆順で削除
            self.db.query(OrderItem).delete()
            self.db.query(Order).delete()
            self.db.query(Product).delete()
            self.db.commit()
            print("データベースクリア完了")

        except Exception as e:
            self.db.rollback()
            print(f"データベースクリアエラー: {e}")


def main():
    """メイン関数"""
    print("テストデータ生成・インポートツール")
    print("1. テストデータ生成（CSV保存）")
    print("2. CSVデータをデータベースにインポート")
    print("3. データベースクリア")
    print("4. 全実行（生成→インポート）")

    choice = input("選択してください (1-4): ")

    if choice == "1":
        generator = TestDataGenerator()
        generator.generate_all_test_data()

    elif choice == "2":
        importer = CSVDataImporter()
        importer.import_all_from_csv()

    elif choice == "3":
        importer = CSVDataImporter()
        importer.clear_all_data()

    elif choice == "4":
        # テストデータ生成
        generator = TestDataGenerator()
        generator.generate_all_test_data()

        # データベースにインポート
        importer = CSVDataImporter()
        importer.import_all_from_csv()

    else:
        print("無効な選択です")


if __name__ == "__main__":
    main()
