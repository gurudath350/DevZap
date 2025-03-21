#!/usr/bin/env python3
import os
import sys
import json
import argparse
import logging
import requests
import threading
import time
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('devzap')

CONFIG_DIR = Path.home() / '.devzap'
CONFIG_FILE = CONFIG_DIR / 'config.json'

class DevZap:
    def __init__(self):
        self.config = self.load_config()
        self.monitor_thread = None
        self.monitor_running = False

    def load_config(self) -> Dict:
        """Load configuration from file or environment, or trigger setup."""
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True)
        
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load config: {e}")
                return self.first_time_setup()
        
        api_key = os.getenv('DEVZAP_API_KEY')
        model = os.getenv('DEVZAP_MODEL', 'microsoft/phi-3-medium-128k-instruct')
        if api_key:
            config = {
                'api_key': api_key,
                'model': model,
                'error_monitoring': {'enabled': True, 'scan_interval': 300, 'log_patterns': [r'error:', r'exception']}
            }
            self.save_config(config)
            return config
        
        logger.info("No config found. Running setup...")
        return self.first_time_setup()

    def save_config(self, config: Dict) -> None:
        """Save configuration to file."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Config saved successfully.")
        except IOError as e:
            logger.error(f"Failed to save config: {e}")

    def first_time_setup(self) -> Dict:
        """Interactive setup for initial configuration."""
        print("\n=== DevZap Setup ===")
        config = {}
        
        api_key = self._prompt_api_key()
        config['api_key'] = api_key
        
        models = self.get_available_models(api_key)
        config['model'] = self._prompt_model(models)
        
        config['error_monitoring'] = {
            'enabled': True,
            'scan_interval': 300,
            'log_patterns': [r'error:', r'exception', r'failed', r'critical']
        }
        
        self.save_config(config)
        print("Setup completed!")
        return config

    def _prompt_api_key(self) -> str:
        """Prompt and validate API key."""
        while True:
            print("\nEnter OpenRouter API key: ", end='', flush=True)
            api_key = sys.stdin.readline().strip()
            if self.validate_openrouter_api_key(api_key):
                return api_key
            print("Invalid API key. Try again.")

    def _prompt_model(self, models: List[str]) -> str:
        """Prompt user to select a model."""
        print("\nAvailable Models:")
        for i, model in enumerate(models, 1):
            print(f"{i}. {model}")
        while True:
            print("\nSelect model (number) or enter custom ID: ", end='', flush=True)
            choice = sys.stdin.readline().strip()
            try:
                if choice.isdigit() and 1 <= int(choice) <= len(models):
                    return models[int(choice) - 1]
                if choice:
                    return choice
                print("Invalid input. Enter a number or custom ID.")
            except ValueError:
                print("Invalid input. Try again.")

    def validate_openrouter_api_key(self, api_key: str) -> bool:
        """Validate OpenRouter API key."""
        if not api_key:
            return False
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        try:
            response = requests.get('https://openrouter.ai/api/v1/auth/key', headers=headers, timeout=10)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"API key validation failed: {e}")
            return False

    def get_available_models(self, api_key: str) -> List[str]:
        """Fetch available models from OpenRouter or return fallback list."""
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        try:
            response = requests.get('https://openrouter.ai/api/v1/models', headers=headers, timeout=10)
            response.raise_for_status()
            models_data = response.json()
            models = [model.get('id') for model in models_data.get('data', []) if model.get('id')]
            return models or self._get_fallback_models()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch models: {e}")
            return self._get_fallback_models()

    def _get_fallback_models(self) -> List[str]:
        """Return fallback model list optimized for coding."""
        return [
            "microsoft/phi-3-medium-128k-instruct",
            "microsoft/phi-3-mini-128k-instruct",
            "meta-llama/llama-3-8b-instruct",
            "mistralai/mistral-7b-instruct",
            "openai/gpt-4o"
        ]

    def _call_openrouter_api(self, prompt: str) -> str:
        """Generic API call to OpenRouter."""
        headers = {'Authorization': f'Bearer {self.config["api_key"]}', 'Content-Type': 'application/json'}
        data = {
            'model': self.config['model'],
            'messages': [{'role': 'user', 'content': prompt}]
        }
        try:
            response = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.RequestException as e:
            logger.error(f"API call failed: {e}")
            return f"Error: API request failed - {str(e)}"

    def _extract_commands(self, response: str) -> List[str]:
        """Extract shell commands from markdown response (lines starting with `$`)."""
        commands = []
        for line in response.split('\n'):
            if line.strip().startswith('$'):
                command = line.strip()[1:].strip()
                if command:
                    commands.append(command)
        return commands

    def _execute_command(self, command: str, auto: bool = False) -> bool:
        """Execute a shell command with optional confirmation."""
        if not auto:
            print(f"\nProposed command: {command}")
            confirm = input("Execute? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Command skipped.")
                return False
        
        try:
            result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
            print(f"Command output:\n{result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            print(f"Error executing command: {e.stderr}")
            return False

    def analyze_error(self, error_text: str, auto: bool = False) -> str:
        """Analyze an error and optionally execute fixes."""
        prompt = f"""You are a DevOps AI assistant. Analyze this error:

