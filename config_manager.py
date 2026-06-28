# config_manager.py
# ======================================
# 設定管理システム
# キーバインディング・コントローラー設定の保存と読み込み
# ======================================

import json
import os
import pygame
from pathlib import Path

from game_paths import path_in_save_dir


class ConfigManager:
    """キーバインディング・コントローラー設定の永続化を管理するクラス。"""
    
    # 設定ファイル名（保存先は get_save_dir = EXEと同じフォルダ）
    CONFIG_FILENAME = "game_config.json"
    
    # デフォルト設定
    DEFAULT_KEY_BINDINGS = {
        "up": pygame.K_UP,
        "down": pygame.K_DOWN,
        "left": pygame.K_LEFT,
        "right": pygame.K_RIGHT,
        "shoot": pygame.K_SPACE,
        "ems": pygame.K_e,
        "pause": pygame.K_q,
        "weapon_mode": pygame.K_r,
    }
    
    DEFAULT_CONTROLLER = {
        "shoot": 0,
        "confirm": 0,
        "cancel": 1,
        "ems": 3,
        "pause": 7,
        "weapon_mode": 2,
        "axis_x": 0,
        "axis_y": 1,
        "dpad_x": 0,
        "dpad_y": 1,
        "deadzone": 0.25,
    }
    
    def __init__(self):
        """ConfigManager を初期化。既存の設定があれば読み込む。"""
        self.config_path = path_in_save_dir(self.CONFIG_FILENAME)
        self.key_bindings = self.DEFAULT_KEY_BINDINGS.copy()
        self.controller = self.DEFAULT_CONTROLLER.copy()
        self.load()
        self._merge_missing_defaults()
    
    # --------------------------------------------------
    # 設定ファイルの読み込み
    # --------------------------------------------------
    def load(self):
        """JSON ファイルから設定を読み込む。
        
        ファイルが存在しない or パースエラーの場合はデフォルト値を保持。
        """
        try:
            if not os.path.exists(self.config_path):
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # キーバインディングの読み込み
            if "key_bindings" in data and isinstance(data["key_bindings"], dict):
                kb = data["key_bindings"]
                # 文字列キーを pygame の定数に変換
                for key, val in kb.items():
                    if isinstance(val, str) and val.startswith("K_"):
                        # "K_UP" → pygame.K_UP に変換
                        try:
                            pygame_key = getattr(pygame, val)
                            self.key_bindings[key] = pygame_key
                        except AttributeError:
                            pass
            
            # コントローラー設定の読み込み
            if "controller" in data and isinstance(data["controller"], dict):
                self.controller.update(data["controller"])

            self._merge_missing_defaults()
        
        except Exception as e:
            # ロード失敗はデフォルト値で継続
            print(f"[ConfigManager] Failed to load config: {e}")

    def _merge_missing_defaults(self):
        """旧設定ファイルに無いキーをデフォルトで補完。"""
        for key, val in self.DEFAULT_KEY_BINDINGS.items():
            if key not in self.key_bindings:
                self.key_bindings[key] = val
        for key, val in self.DEFAULT_CONTROLLER.items():
            if key not in self.controller:
                self.controller[key] = val
    
    # --------------------------------------------------
    # 設定ファイルの保存
    # --------------------------------------------------
    def save(self):
        """現在の設定を JSON ファイルに保存。
        
        pygame の key 定数（整数）を文字列（"K_UP" など）に変換して保存。
        """
        try:
            # pygame key を文字列に変換（逆引き）
            kb_str = {}
            for key, val in self.key_bindings.items():
                pygame_name = self._pygame_key_to_name(val)
                kb_str[key] = pygame_name
            
            data = {
                "key_bindings": kb_str,
                "controller": self.controller
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"[ConfigManager] Failed to save config: {e}")
    
    # --------------------------------------------------
    # pygame key 定数の名前変換
    # --------------------------------------------------
    @staticmethod
    def _pygame_key_to_name(key_code):
        """pygame のキーコード(整数)を文字列名に変換。
        
        例: pygame.K_UP → "K_UP"
        """
        # pygame.K_xxx の名前を逆引き
        for name in dir(pygame):
            if name.startswith("K_"):
                if getattr(pygame, name) == key_code:
                    return name
        return f"K_UNKNOWN_{key_code}"
    
    # --------------------------------------------------
    # 設定の更新（ゲーム実行中の反映用）
    # --------------------------------------------------
    def set_key_binding(self, action, key_code):
        """指定アクションのキーバインディングを更新。
        
        Args:
            action (str): "shoot", "up" など
            key_code (int): pygame キーコード
        """
        if action in self.key_bindings:
            self.key_bindings[action] = key_code
            self.save()
    
    def set_controller_button(self, action, button):
        """指定アクションのコントローラーボタンを更新。
        
        Args:
            action (str): "shoot", "ems" など
            button (int): ボタン番号
        """
        if action in self.controller:
            self.controller[action] = button
            self.save()
    
    # --------------------------------------------------
    # 設定のリセット
    # --------------------------------------------------
    def reset_to_default(self):
        """全ての設定をデフォルト値にリセット。"""
        self.key_bindings = self.DEFAULT_KEY_BINDINGS.copy()
        self.controller = self.DEFAULT_CONTROLLER.copy()
        self.save()
    
    # --------------------------------------------------
    # 設定の取得（読み取り専用）
    # --------------------------------------------------
    def get_key_binding(self, action):
        """指定アクションのキーコードを取得。"""
        return self.key_bindings.get(action, pygame.K_UNKNOWN)
    
    def get_all_key_bindings(self):
        """全キーバインディングを取得。"""
        return self.key_bindings.copy()
    
    def get_controller(self):
        """全コントローラー設定を取得。"""
        return self.controller.copy()
