from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_DB_URI: str

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

# Create an instance of your settings
settings = Settings()

# You can now access your settings
print(f'MongoDB URI: {settings.MONGO_DB_URI}')