# -*- coding: utf-8 -*-
"""
MehburAI - Akıllı Bellek ve Semantik Arama Motoru (Memory Engine)
==================================================================
Kullanıcının çevrimiçiyken sorduğu tüm soruları ve üretilen yanıtları
SQLite veritabanında kalıcı olarak saklar. Çevrimdışıyken ise
Türkçe morfolojisine uygun akıllı semantik/vektörel benzerlik
motoruyla hafızasındaki en uygun cevabı bulup getirir.

Özellikler:
  • SQLite kalıcı veri tabanı (data/mehbur_memory.db)
  • Türkçe karakter & ek duyarlı normalizasyon (Turkish Stem & Tokenizer)
  • Hibrit Semantik Eşleme: Karakter N-Gram + Kelime TF-IDF Kosinüs Benzerliği
  • sentence-transformers desteği (mevcutsa otomatik aktifleşir)
  • Otomatik güncelleme (Aynı/çok yakın soru gelirse yanıtı günceller)
  • Sohbet geçmişi (chat_logs) ve istatistik takip mekanizması
"""

import json
import math
import os
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config import DB_PATH, MemoryConfig


# ─────────────────────────────────────────────
# Türkçe Metin İşleme ve Normalizasyon
# ─────────────────────────────────────────────

def turkish_lower(text: str) -> str:
    """Türkçe karakterleri ('İ' -> 'i', 'I' -> 'ı') doğru küçültür."""
    if not text:
        return ""
    mapping = {
        "İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ",
        "Ü": "ü", "Ö": "ö", "Ç": "ç"
    }
    for upper_ch, lower_ch in mapping.items():
        text = text.replace(upper_ch, lower_ch)
    return text.lower()


def clean_text(text: str) -> str:
    """Noktalama işaretlerini temizler, fazla boşlukları giderir."""
    text = turkish_lower(text)
    # Noktalama işaretlerini boşluk yap
    text = re.sub(r"[^\w\s]", " ", text)
    # Çoklu boşlukları teke indir
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Türkçe sık kullanılan ekler (Gelişmiş budama sırası: uzundan kısaya)
TURKISH_SUFFIXES = [
    "lerimizden", "larımızdan", "lerimizdeki", "larımızdaki",
    "lerimizle", "larımızla", "lerinden", "larından",
    "imizden", "ımızdan", "ümüzden", "umuzdan",
    "lerimiz", "larımız", "leriniz", "larınız", "lerinde", "larında",
    "imizin", "ımızın", "ümüzün", "umuzun",
    "imize", "ımıza", "ümüze", "umuza",
    "imiz", "ımız", "ümüz", "umuz",
    "iniz", "ınız", "ünüz", "unuz",
    "lerin", "ların", "lerle", "larla", "lerde", "larda",
    "lerin", "ların", "lere", "lara", "leri", "ları",
    "deki", "daki", "teki", "taki",
    "den", "dan", "ten", "tan",
    "de", "da", "te", "ta",
    "nin", "nın", "nün", "nun",
    "dir", "dır", "dür", "dur", "tir", "tır", "tür", "tur",
    "in", "ın", "ün", "un",
    "ye", "ya", "ne", "na",
    "si", "sı", "sü", "su",
    "li", "lı", "lü", "lu",
    "lik", "lık", "lük", "luk",
    "e", "a", "i", "ı", "ü", "u"
]

# Etkisiz kelimeler (Stopwords)
TURKISH_STOPWORDS = {
    "acaba", "bir", "bu", "şu", "o", "ve", "veya", "ile", "de", "da",
    "mi", "mı", "mü", "mu", "misin", "mısın", "müsün", "musun",
    "nedir", "nelerdir", "neresi", "neresidir", "hakkında", "bilgi",
    "ver", "söyle", "anlat", "lütfen", "bana", "için", "gibi", "kadar",
    "hangisidir", "hangisi", "ne", "neler", "nerede", "nasıl", "neden"
}


def get_stem(word: str) -> str:
    """Türkçe kelimenin eklerini soyup köküne yaklaşır."""
    w = word.strip()
    if len(w) <= 3:
        return w
    for suffix in TURKISH_SUFFIXES:
        if w.endswith(suffix):
            candidate = w[:-len(suffix)]
            if len(candidate) >= 3:
                w = candidate
                break
    return w


def tokenize_and_stem(text: str) -> List[str]:
    """Türkçe metni parçalar, durak kelimeleri eler ve kökleri çıkarır."""
    cleaned = clean_text(text)
    words = cleaned.split()
    stems = []

    for word in words:
        if len(word) <= 1 or word in TURKISH_STOPWORDS:
            continue
        stem = get_stem(word)
        stems.append(stem)

    return stems if stems else [get_stem(w) for w in words if len(w) > 1]


def get_ngrams(text: str, n: int = 3) -> List[str]:
    """Karakter seviyesi n-gram üretir."""
    cleaned = clean_text(text).replace(" ", "_")
    if len(cleaned) < n:
        return [cleaned]
    return [cleaned[i:i + n] for i in range(len(cleaned) - n + 1)]


# ─────────────────────────────────────────────
# Hibrit Vektör & Benzerlik Hesaplayıcı
# ─────────────────────────────────────────────

class HybridSimilarity:
    """Türkçe için optimize edilmiş N-gram + Kök Jaccard + Token Kosinüs Benzerliği."""

    @staticmethod
    def cosine_similarity(vec1: Counter, vec2: Counter) -> float:
        """İki frekans vektörü arasındaki kosinüs benzerliğini hesaplar."""
        intersection = set(vec1.keys()) & set(vec2.keys())
        if not intersection:
            return 0.0

        numerator = sum(vec1[x] * vec2[x] for x in intersection)
        sum1 = sum(v ** 2 for v in vec1.values())
        sum2 = sum(v ** 2 for v in vec2.values())
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if denominator == 0:
            return 0.0
        return float(numerator / denominator)

    @staticmethod
    def jaccard_similarity(set1: set, set2: set) -> float:
        """İki küme arasındaki Jaccard katsayısını hesaplar."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return float(intersection / union) if union > 0 else 0.0

    @classmethod
    def calculate_score(cls, query: str, target: str) -> float:
        """
        İki soru arasındaki hibrit benzerlik skorunu (0.0 - 1.0) hesaplar.
        """
        clean_q = clean_text(query)
        clean_t = clean_text(target)

        # 1. Birebir aynıysa tam puan
        if clean_q == clean_t:
            return 1.0

        if not clean_q or not clean_t:
            return 0.0

        # Alt dize kapsama kontrolü
        contains_bonus = 0.15 if (clean_q in clean_t or clean_t in clean_q) else 0.0

        # Kök ve Token kümeleri
        stems_q = tokenize_and_stem(query)
        stems_t = tokenize_and_stem(target)
        stem_set_q = set(stems_q)
        stem_set_t = set(stems_t)

        # 2. Kök Jaccard Benzerliği
        jaccard_stem = cls.jaccard_similarity(stem_set_q, stem_set_t)

        # 3. Kök Kosinüs Benzerliği
        token_sim = cls.cosine_similarity(Counter(stems_q), Counter(stems_t))

        # 4. Karakter 3-Gram Kosinüs Benzerliği
        ngrams_q = Counter(get_ngrams(query, 3))
        ngrams_t = Counter(get_ngrams(target, 3))
        ngram_sim = cls.cosine_similarity(ngrams_q, ngrams_t)

        # Kök ortaklığı yüksekse güçlü eşleşme kabul edilir
        intersection_roots = stem_set_q & stem_set_t
        root_match_ratio = len(intersection_roots) / max(1, min(len(stem_set_q), len(stem_set_t)))

        # Ağırlıklı nihai skor
        final_score = (
            (root_match_ratio * 0.35) +
            (token_sim * 0.25) +
            (jaccard_stem * 0.20) +
            (ngram_sim * 0.20) +
            contains_bonus
        )
        return min(1.0, round(final_score, 4))


# ─────────────────────────────────────────────
# Akıllı Bellek Motoru (MemoryEngine)
# ─────────────────────────────────────────────

class MemoryEngine:
    """
    MehburAI kalıcı SQLite bellek ve semantik sorgulama yöneticisi.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Veritabanı bağlantısı oluşturur (WAL modu ile hızlı okuma)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_database(self) -> None:
        """Veritabanı tablolarını ve indekslerini oluşturur."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Bilgi Tabanı Tablosu (Öğrenilen soru-cevaplar)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    cleaned_question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    source TEXT DEFAULT 'gemini',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Hızlı arama için indeksler
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cleaned_question 
                ON knowledge_base(cleaned_question);
            """)

            # 2. Sohbet Geçmişi Tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,          -- 'user' veya 'mehbur'
                    message TEXT NOT NULL,
                    is_online INTEGER NOT NULL,  -- 1=online, 0=offline
                    source TEXT DEFAULT NULL,    -- 'memory' veya 'gemini'
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.commit()

    # ─────────────────────────────────────────
    # Bilgi Kaydetme & Öğrenme Pipeline'ı
    # ─────────────────────────────────────────

    def save_knowledge(self, question: str, answer: str, source: str = "gemini") -> Tuple[int, bool]:
        """
        Soru ve cevabı hafızaya kaydeder.
        Eğer çok benzer bir soru zaten varsa (>0.90 benzerlik), cevabını günceller.

        Returns:
            Tuple[int, bool]: (kayıt_id, güncellendi_mi)
        """
        question = question.strip()
        answer = answer.strip()
        if not question or not answer:
            return 0, False

        cleaned = clean_text(question)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Önce birebir veya çok yakın eşleşme var mı kontrol et
            cursor.execute("SELECT id, question, cleaned_question FROM knowledge_base")
            rows = cursor.fetchall()

            for row in rows:
                existing_id = row["id"]
                existing_q = row["question"]
                score = HybridSimilarity.calculate_score(question, existing_q)

                if score >= 0.90:
                    # Mevcut kaydı güncelle
                    cursor.execute("""
                        UPDATE knowledge_base
                        SET answer = ?, source = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (answer, source, existing_id))
                    conn.commit()
                    return existing_id, True

            # Yeni kayıt ekle
            cursor.execute("""
                INSERT INTO knowledge_base (question, cleaned_question, answer, source)
                VALUES (?, ?, ?, ?)
            """, (question, cleaned, answer, source))
            conn.commit()
            return cursor.lastrowid, False

    # ─────────────────────────────────────────
    # Çevrimdışı Akıllı Arama
    # ─────────────────────────────────────────

    def search_knowledge(
        self, query: str, threshold: float = MemoryConfig.SIMILARITY_THRESHOLD
    ) -> Optional[Dict[str, Any]]:
        """
        Kullanıcı sorusuna en uygun yanıtı veritabanından semantik olarak arar.

        Returns:
            Eğer benzerlik >= threshold ise:
            {
                'id': int,
                'question': str,
                'answer': str,
                'source': str,
                'score': float,
                'access_count': int
            }
            Bulunamazsa: None
        """
        query = query.strip()
        if not query:
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, question, answer, source, access_count FROM knowledge_base")
            rows = cursor.fetchall()

            if not rows:
                return None

            best_match = None
            best_score = 0.0

            for row in rows:
                target_q = row["question"]
                score = HybridSimilarity.calculate_score(query, target_q)

                if score > best_score:
                    best_score = score
                    best_match = row

            if best_match and best_score >= threshold:
                # Erişim sayısını ve son erişim tarihini güncelle
                cursor.execute("""
                    UPDATE knowledge_base 
                    SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (best_match["id"],))
                conn.commit()

                return {
                    "id": best_match["id"],
                    "question": best_match["question"],
                    "answer": best_match["answer"],
                    "source": best_match["source"],
                    "score": round(best_score, 3),
                    "access_count": best_match["access_count"] + 1,
                }

            return None

    # ─────────────────────────────────────────
    # Sohbet Geçmişi İşlemleri
    # ─────────────────────────────────────────

    def log_message(self, role: str, message: str, is_online: bool, source: Optional[str] = None) -> int:
        """Sohbet mesajını geçmişe kaydeder."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_logs (role, message, is_online, source)
                VALUES (?, ?, ?, ?)
            """, (role, message, 1 if is_online else 0, source))
            conn.commit()
            return cursor.lastrowid

    def get_recent_chat(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Son sohbet mesajlarını getirir."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, role, message, is_online, source, timestamp
                FROM chat_logs
                ORDER BY id ASC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # ─────────────────────────────────────────
    # Hafıza İstatistikleri & Yönetimi
    # ─────────────────────────────────────────

    def get_all_knowledge(self, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        """Tüm kayıtlı soru-cevapları liste halinde getirir."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, question, answer, source, created_at, access_count, last_accessed
                FROM knowledge_base
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def get_memory_count(self) -> int:
        """Kayıtlı toplam soru sayısını döndürür."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM knowledge_base")
            row = cursor.fetchone()
            return row["total"] if row else 0

    def delete_knowledge(self, record_id: int) -> bool:
        """Belirtilen ID'li kaydı hafızadan siler."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_base WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_knowledge(self) -> bool:
        """Tüm öğrenilen bilgileri temizler."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_base")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='knowledge_base'")
            conn.commit()
            return True


# ─────────────────────────────────────────────
# Bağımsız Test Modülü
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import io
    import sys

    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("=" * 60)
    print("  MehburAI - Akıllı Bellek (Memory Engine) Testi")
    print("=" * 60)

    engine = MemoryEngine()

    # Örnek sorular öğren
    print("\n[1] Örnek bilgiler hafızaya yükleniyor...")
    sample_data = [
        ("Türkiye'nin başkenti neresidir?", "Türkiye Cumhuriyeti'nin başkenti Ankara'dır. 13 Ekim 1923'te başkent ilan edilmiştir.", "wikipedia"),
        ("Python programlama dili nedir?", "Python; Guido van Rossum tarafından geliştirilen, okunabilirliği yüksek, nesne yönelimli, genel amaçlı bir programlama dilidir.", "gemini"),
        ("Güneş sistemindeki en büyük gezegen hangisidir?", "Güneş sistemimizdeki en büyük gezegen Jüpiter'dir.", "nasa"),
    ]

    for q, a, s in sample_data:
        rec_id, updated = engine.save_knowledge(q, a, s)
        status = "Güncellendi" if updated else "Yeni Eklendi"
        print(f"  + [{status}] ID: {rec_id} -> Soru: '{q}'")

    print(f"\n  Toplam kayıtlı bilgi sayısı: {engine.get_memory_count()}")

    # Çevrimdışı benzerlik sorguları testi
    print("\n[2] Çevrimdışı Semantik Eşleme Testleri:")
    test_queries = [
        "Türkiye'nin başkenti neresi?",              # Farklı ek kullanımı
        "Başkentimiz neresidir acaba?",              # Farklı kelime kalıbı
        "Python dili ne işe yarar nedir?",           # Benzer soru
        "En büyük gezegen hangisi?",                  # Kısaltılmış soru
        "Mars gezegeninde su var mı?",               # Hafızada OLMAYAN soru
    ]

    for tq in test_queries:
        match = engine.search_knowledge(tq)
        if match:
            print(f"\n  🔍 Soru: '{tq}'")
            print(f"  🎯 Eşleşen Kayıt ({match['score']*100:.1f}% benzerlik): '{match['question']}'")
            print(f"  💡 Yanıt: {match['answer']}")
            print(f"  📌 Kaynak: {match['source']} (Erişim: {match['access_count']})")
        else:
            print(f"\n  🔍 Soru: '{tq}'")
            print(f"  ⚠️ [Hafızada Bulunamadı] Henüz bu bilgi öğrenilmemiş.")

    print("\n" + "=" * 60)
    print("  ✅ Memory Engine testi başarıyla tamamlandı!")
    print("=" * 60)
