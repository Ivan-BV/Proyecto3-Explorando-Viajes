from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
from time import sleep
import random
from tqdm import tqdm

def calcular_num_paginas(url):
    """
    Calcula el número total de páginas de resultados en una URL específica.

    Esta función realiza una solicitud GET a la URL proporcionada y analiza el contenido HTML 
    para extraer el número total de resultados. Luego, calcula el número de páginas necesarias
    asumiendo que cada página muestra un máximo de 40 resultados.

    Parámetros:
    url (str): La URL de la cual se desea obtener el número de páginas.

    Retorna:
    int: El número total de páginas necesarias para mostrar todos los resultados. Si la solicitud
    falla o el elemento con el número total de resultados no se encuentra, se devuelve None.
    """
    res = requests.get(url)
    if res.status_code == 200:
        sopa = BeautifulSoup(res.content, "html.parser")
        resultado = sopa.find("h1", "nresultados title")
        total = int(resultado.text.split(" ")[0])
        return int(np.ceil(total/40))
    else:
        print(f"Error en la conexión con la url {res.status_code}")

def buscar_actividades(url: str):
    df_actividades_final = pd.DataFrame()
    num_paginas = calcular_num_paginas(url.format("1"))
    for pagina in tqdm(range(1, num_paginas+1)):
        url_formateada = url.format(pagina)
        res = requests.get(url_formateada)
        if res.status_code == 200:
            sopa = BeautifulSoup(res.content, "html.parser")
            resultados = sopa.find("div", {"id": "resultados_container"})
            card_results = resultados.find_all("div", {"class": "card-result"})
            if len(card_results) > 0:
                resultados_imagenes = [f"https://www.atrapalo.com{card.find('img', {'class': 'lazy event-img'}).get('data-original')}" if card.find("img", {'class': 'lazy event-img'}) is not None else pd.NA for card in card_results]
                df_imagenes = pd.DataFrame(resultados_imagenes, columns=["imagen"])
                df_imagenes.dropna(inplace=True)
                resultados_ratings = [card.find("div", {"class": "score background-opi-very-good"}) if card.find("div", {"class": "score background-opi-very-good"}) is not None else pd.NA for card in card_results]
                ratings_filtrado = [rating.find("span", {"class": "opi-rating"}) if rating is not pd.NA else pd.NA for rating in resultados_ratings]
                ratings_limpio = [str(rating.getText()).replace("\n", "").strip() if rating is not pd.NA else "Sin puntuación" for rating in ratings_filtrado]
                nombres_limpios = [str(resultado.find("span").getText()).replace("\n", "").strip() for resultado in resultados.find_all("h2", {"class": "clear nombre"})]
                resultados_lugares = [resultado.find("span", {"class": "locality GATrackEvent_ubicacion show-for-small-only"}) if resultado.find("span", {"class": "locality GATrackEvent_ubicacion show-for-small-only"}) is not None else resultado.find("span") for resultado in resultados.find_all("p", {"class": "info"})]
                texto_lugares = [lugar.getText() if lugar is not None else pd.NA for lugar in resultados_lugares]
                df_lugares = pd.DataFrame(texto_lugares, columns=["lugar"]).dropna()
                condicion = df_lugares["lugar"].str.startswith("2") == False
                condicion2 = df_lugares["lugar"].str.startswith("1") == False
                df_lugares_filtrado = df_lugares[condicion & condicion2]
                df_lugares_limpio = df_lugares_filtrado["lugar"].str.replace("\n", "").replace("\xa0", "").replace("(Barcelona)", "").str.strip().reset_index().drop(columns=["index"])
                resultados_secciones = [resultado.find("span", {"class": "type large-loc"}) for resultado in resultados.find_all("p", {"class": "info"})]
                texto_secciones = [seccion.getText() if seccion is not None else pd.NA for seccion in resultados_secciones]
                df_secciones = pd.DataFrame(texto_secciones, columns=["categoria"]).dropna()
                df_secciones_limpio = df_secciones["categoria"].str.replace("\n", "").str.strip().reset_index().drop(columns=["index"])
                precios = [precio.getText() for precio in resultados.find_all("span", {"class": "value"})]
                df_precios = pd.DataFrame(precios, columns=["precio"])
                df_precios_limpio = df_precios["precio"].str.replace("\n", "").str.strip()
                df_actividades_concatenadas = pd.concat([pd.DataFrame(nombres_limpios, columns=["nombre_actividad"]), df_lugares_limpio, df_secciones_limpio, pd.DataFrame(ratings_limpio, columns=["puntuacion"]), df_imagenes, df_precios_limpio], axis=1)
                df_actividades_concatenadas["puntuacion"].fillna("Sin puntuación", axis=0, inplace=True)
                df_actividades_concatenadas["imagen"].fillna("Sin imagen", axis=0, inplace=True)
                df_actividades_limpio = df_actividades_concatenadas
                df_actividades_final = pd.concat([df_actividades_final, df_actividades_limpio], axis=0)
                sleep(random.randint(1, 3))
            else:
                print("No hay más resultados")
                break
        else:
            print(f"Error en la conexión con la url {res.status_code}")
    df_actividades_final.reset_index(inplace=True)
    df_actividades_final.drop(columns=["index"], inplace=True)
    df_actividades_final.drop_duplicates(inplace=True)
    df_actividades_final.dropna(inplace=True)
    return df_actividades_final

def buscar_vuelos(url, querystring, key):
    headers = {
	"x-rapidapi-key": key,
	"x-rapidapi-host": "booking-com18.p.rapidapi.com"
    }

    res = requests.get(url, headers=headers, params=querystring)
    if res.status_code == 200:
        datos = dict(res.json()).get("data")
        vuelos = datos.get("flights", [])

        resultados = []
        
        for vuelo in vuelos:
            for destino in vuelo["bounds"]:
                for segmento in destino["segments"]:
                    hora_salida = segmento.get("departuredAt", pd.NA)
                    hora_llegada = segmento.get("arrivedAt", pd.NA)
                    numero_vuelo = segmento["flightNumber"]
                    compañia_marketing = segmento["marketingCarrier"]["name"]
                    numero_paradas = segmento["numberOfTechnicalStops"]
                    clase_cabina = segmento["cabinClassName"]
                    fecha_salida = hora_salida[:10]
                    fecha_llegada = hora_llegada[:10]
                    info_precio = vuelo.get("travelerPrices")[0]
                    precio = info_precio.get("price").get("markup").get("value", pd.NA)

                    resultados.append({
                        "compañía": compañia_marketing,
                        "fecha de ida": fecha_salida,
                        "hora de salida": hora_salida[11:],
                        "fecha de llegada": fecha_llegada,
                        "hora de llegada": hora_llegada[11:],
                        "número de paradas": numero_paradas,
                        "número de vuelo": numero_vuelo,
                        "clase": clase_cabina,
                        "precio": f"{np.round(int(precio)*0.92, 2)} €",
                    })

        df_vuelos = pd.DataFrame(resultados)
        return df_vuelos
    else:
        print(f"Error en la conexión con la url {res.status_code}")

def obtener_cod_region(url, querystring, key):

    headers = {
        "x-rapidapi-key": key,
        "x-rapidapi-host": "hotels-com-provider.p.rapidapi.com"
    }

    res = requests.get(url, headers=headers, params=querystring)

    if res.status_code == 200:
        datos = res.json().get("data")[0]
        cod_region = datos.get("gaiaId", pd.NA)
        return cod_region
    else:
        print(f"Error en la conexión con la url {res.status_code}")
    
def buscar_hoteles(url, querystring, key):
    headers = {
	"x-rapidapi-key": key,
	"x-rapidapi-host": "hotels-com-provider.p.rapidapi.com"
    }

    res = requests.get(url, headers=headers, params=querystring)
    if res.status_code == 200:
        datos = res.json().get("data")
        properties = datos.get("properties", [])

        resultados = []
        
        for property in properties:
            id_hotel = property.get("id", pd.NA)
            nombre_hotel = property.get("name", pd.NA)
            servicios = property.get("short_amenities", pd.NA)
            calificacion_huesped = property.get("guestRating").get("rating", pd.NA)
            texto_entero_calificacion = property.get("guestRating").get("ratingText", pd.NA)
            reviews = property.get("guestRating").get("phrases", pd.NA)
            calificacion_estrellas = property.get("star_rating_ids", pd.NA)
            info_precio = property.get("price").get("priceSummary").get("displayPrices", pd.NA)
            
            if info_precio:
                info_precio_formateado = info_precio[0].get("price").get("formatted", pd.NA)
            else:
                info_precio_formateado = pd.NA

            resultados.append({
                "id_hotel": id_hotel,
                "nombre": nombre_hotel,
                "servicios": servicios,
                "calificación": calificacion_huesped,
                "texto calificación": texto_entero_calificacion,
                "comentarios": reviews,
                "estrellas": calificacion_estrellas,
                "precio": info_precio_formateado
            })

        df_hoteles = pd.DataFrame(resultados)
        return df_hoteles
    else:
        print(f"Error en la conexión con la url {res.status_code}")