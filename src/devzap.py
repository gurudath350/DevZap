#!/usr/bin/env python3
import os
import sys
import json
import argparse
import logging
import requests
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('devzap')

CONFIG_DIR = Path.home() / '.devzap'
CONFIG_FILE = CONFIG_DIR / 'config.json'

class DevZap:
    def __init__(self):
        self.config = self.load_config()
        
    def load_config(self):
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True)
        if not CONFIG_FILE.exists():
            logger.info("No config found. Running setup...")
            return self.first_time_setup()
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info("Config loaded.")
                return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.first_time_setup()
    
    def first_time_setup(self):
        print("\n" + "="*50)
        print("Welcome to DevZap Setup!")
        print("="*50)
        config = {}
        print("\nEnter your OpenRouter API key: ", end='', flush=True)
        api_key = sys.stdin.readline().strip()
        if self.validate_openrouter_api_key(api_key):
            config['api_key'] = api_key
        else:
            raise ValueError("Invalid API key.")
        
        print("\nFetching models...")
        models = self.get_available_models(config['api_key'])
        print("\nAvailable Models:")
        for i, model in enumerate(models, 1):
            print(f"{i}. {model}")
        print("\nSelect a model (number) or enter custom ID: ", end='', flush=True)
        choice_input = sys.stdin.readline().strip()
        if choice_input.isdigit() and 1 <= int(choice_input) <= len(models):
            config['model'] = models[int(choice_input)-1]
        else:
            config['model'] = choice_input
        
        config['error_monitoring'] = {'enabled': True, 'scan_interval': 300, 'log_patterns': [r'error:', r'exception']}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print("\nSetup completed!")
        return config
    
    def validate_openrouter_api_key(self, api_key):
        if not api_key:
            return False
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        try:
            response = requests.get('https://openrouter.ai/api/v1/auth/key', headers=headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False
    
    def get_available_models(self, api_key):
        try:
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
            response = requests.get('https://openrouter.ai/api/v1/models', headers=headers, timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                available_models = [model.get('id') for model in models_data.get('data', []) if model.get('id')]
                if not available_models:
                    logger.warning("No models from API, using fallback.")
                    return [
                        "microsoft/phi-3-medium-128k-instruct",
                        "microsoft/phi-3-mini-128k-instruct",
                        "meta-llama/llama-3-8b-instruct",
                        "mistralai/mistral-7b-instruct",
                        "openai/gpt-4o"
                    ]
                return available_models
            else:
                logger.warning(f"Fetch failed: {response.status_code}")
                return [
                    "microsoft/phi-3-medium-128k-instruct",
                    "microsoft/phi-3-mini-128k-instruct",
                    "meta-llama/llama-3-8b-instruct",
                    "mistralai/mistral-7b-instruct",
                    "openai/gpt-4o"
                ]
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return [
                "microsoft/phi-3-medium-128k-instruct",
                "microsoft/phi-3-mini-128k-instruct",
                "meta-llama/llama-3-8b-instruct",
                "mistralai/mistral-7b-instruct",
                "openai/gpt-4o"
            ]
    
    def analyze_error(self, error_text):
        prompt = f"""You are a DevOps AI assistant. Analyze this error:
