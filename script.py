import requests
import matplotlib.pyplot as plt
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from io import BytesIO

# Defina sua chave da API do WeatherAPI e o token do Telegram
API_KEY = '71d046484e5a4390af2204655243011'
TELEGRAM_TOKEN = '7797124115:AAFe1uK4ljuZcIVttA9AXrTECYUVKE5OYvk'

# Função para obter o clima atual e previsão dos próximos 7 dias
def get_weather(city: str) -> tuple[str, BytesIO | None, dict | None]:
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={city}&days=7"
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200 or "error" in data:
            return f"Erro: {data.get('error', {}).get('message', 'Não foi possível obter a previsão.')}", None, None

        location = data['location']['name']
        country = data['location']['country']
        current = data['current']
        forecast = data['forecast']['forecastday']

        # Dados para o gráfico
        dates = [day['date'] for day in forecast]
        max_temps = [day['day']['maxtemp_c'] for day in forecast]
        min_temps = [day['day']['mintemp_c'] for day in forecast]
        rain_chances = [day['day']['daily_chance_of_rain'] for day in forecast]
        humidities = [day['day']['avghumidity'] for day in forecast]

        # Gerar gráficos
        fig, ax = plt.subplots(3, 1, figsize=(8, 12))

        # Gráfico de temperaturas
        ax[0].plot(dates, max_temps, label='Máxima', color='red', marker='o')
        ax[0].plot(dates, min_temps, label='Mínima', color='blue', marker='o')
        ax[0].set_xlabel('Data')
        ax[0].set_ylabel('Temperatura (°C)')
        ax[0].set_title(f"Temperaturas em {location}, {country}")
        ax[0].legend()
        ax[0].grid(True)

        # Gráfico de probabilidade de chuva
        ax[1].bar(dates, rain_chances, color='blue', alpha=0.6)
        ax[1].set_xlabel('Data')
        ax[1].set_ylabel('Probabilidade de Chuva (%)')
        ax[1].set_title(f"Chances de chuva em {location}, {country}")
        ax[1].grid(True)

        # Gráfico de umidade média do ar
        ax[2].plot(dates, humidities, label='Umidade Média', color='green', marker='o')
        ax[2].set_xlabel('Data')
        ax[2].set_ylabel('Umidade (%)')
        ax[2].set_title(f"Umidade média do ar em {location}, {country}")
        ax[2].grid(True)

        # Salvar gráficos em um objeto BytesIO
        img_stream = BytesIO()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(img_stream, format='png')
        img_stream.seek(0)  # Reseta o ponteiro para o início do arquivo

        # Criar a mensagem de texto com a previsão
        weather_info = (
            f"Previsão do tempo para {location}, {country}:\n"
            f"Temperatura atual: {current['temp_c']}°C\n"
            f"Condição: {translate_condition(current['condition']['text'])}\n"
            f"Temperatura máxima hoje: {forecast[0]['day']['maxtemp_c']}°C\n"
            f"Temperatura mínima hoje: {forecast[0]['day']['mintemp_c']}°C\n"
            f"Umidade do ar hoje: {forecast[0]['day']['avghumidity']}%\n"
            f"Probabilidade de chuva hoje: {forecast[0]['day']['daily_chance_of_rain']}%\n\n"
            f"Previsões para os próximos 7 dias:\n"
        )

        for day in forecast:
            date = day['date']
            max_temp = day['day']['maxtemp_c']
            min_temp = day['day']['mintemp_c']
            condition = translate_condition(day['day']['condition']['text'])
            rain_chance = day['day']['daily_chance_of_rain']
            avg_humidity = day['day']['avghumidity']
            weather_info += (
                f"\n{date}:\n"
                f"Temperatura máxima: {max_temp}°C\n"
                f"Temperatura mínima: {min_temp}°C\n"
                f"Condição: {condition}\n"
                f"Probabilidade de chuva: {rain_chance}%\n"
                f"Umidade média do ar: {avg_humidity}%\n"
            )

        # Retorna também os dados do dia atual para a verificação
        return weather_info, img_stream, forecast[0]['day']

    except requests.exceptions.RequestException as e:
        return f"Erro ao se conectar à API: {e}", None, None
    except KeyError as e:
        return f"Erro ao processar dados da API: {e}", None, None

# Função de tradução de condições climáticas
def translate_condition(condition: str) -> str:
    condition_translations = {
        "sunny": "Ensolarado",
        "partly cloudy": "Parcialmente nublado",
        "cloudy": "Nublado",
        "overcast": "Encoberto",
        "mist": "Neblina",
        "patchy rain possible": "Possibilidade de chuva localizada",
        "rain": "Chuva",
        "thunderstorm": "Trovoada",
        "snow": "Neve",
        "clear": "Limpo",
        "moderate rain": "Chuva moderada",
        "patchy rain nearby": "Chuva irregular nas proximidades",
        "heavy rain": "Chuva forte",
        "light rain shower": "Chuva amena"
    }
    return condition_translations.get(condition.lower(), condition)

# Função para lidar com mensagens do usuário
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    city = update.message.text  # Captura o texto enviado pelo usuário
    weather_info, img_stream, today_weather = get_weather(city)

    # Envia a previsão
    await update.message.reply_text(weather_info)
    if img_stream:
        await update.message.reply_photo(photo=img_stream)

    # Verifica condições climáticas
    if today_weather:
        max_temp = today_weather.get('maxtemp_c')
        avg_humidity = today_weather.get('avghumidity')

        if max_temp is not None and avg_humidity is not None:
            if max_temp > 36 and avg_humidity <= 20:
                await update.message.reply_text(
                    "⚠️ As condições de umidade do ar e temperatura favorecem o "
                    "aparecimento de focos de queimadas. Fique atento e contate a defesa "
                    "civil se necessário."
                )
                await update.message.reply_text(
                    "Olá! Digite o nome de uma cidade para saber a previsão do tempo e receber informações adicionais sobre clima. 🌦️"
                )
            elif avg_humidity > 70:
                await update.message.reply_text(
                    "🌱 As condições de umidade do ar favorecem o plantio."
                )
                await update.message.reply_text(
                    "Olá! Digite o nome de uma cidade para saber a previsão do tempo e receber informações adicionais sobre clima. 🌦️"
                )

# Função inicial para /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Olá! Digite o nome de uma cidade para saber a previsão do tempo e receber informações adicionais sobre clima. 🌦️"
    )

# Função principal
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Adiciona handlers para mensagens e comando /start
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
