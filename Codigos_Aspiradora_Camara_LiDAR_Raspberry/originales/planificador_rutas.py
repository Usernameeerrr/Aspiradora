"""Planifica rutas sobre una cuadrícula del LiDAR. Coordenadas: fila, columna."""
import argparse
import csv
import json
import math
from collections import Counter, deque
from functools import lru_cache
from heapq import heappop, heappush
from itertools import count
from pathlib import Path
from time import perf_counter

ALGORITMOS = ("BFS", "UCS", "GREEDY", "A*")


def planificar(libre, inicio, meta, algoritmo, margen=0):
    """Devuelve la ruta, su costo y las extracciones válidas de la frontera."""
    if algoritmo not in ALGORITMOS or margen < 0:
        raise ValueError("Algoritmo o margen inválido")
    filas, columnas = len(libre), len(libre[0])
    disco = [
        (df, dc)
        for df in range(-margen, margen + 1)
        for dc in range(-margen, margen + 1)
        if df * df + dc * dc <= margen * margen
    ]

    @lru_cache(maxsize=None)
    def transitable(celda):
        fila, columna = celda
        return all(
            0 <= fila + df < filas and 0 <= columna + dc < columnas
            and libre[fila + df][columna + dc]
            for df, dc in disco
        )

    def prioridad(celda, costo):
        estimacion = abs(celda[0] - meta[0]) + abs(celda[1] - meta[1])
        if algoritmo == "GREEDY":
            return estimacion
        if algoritmo == "A*":
            return costo + estimacion
        return costo

    for nombre, celda in (("inicio", inicio), ("meta", meta)):
        if not transitable(celda):
            raise ValueError(f"{nombre} {celda} fuera del espacio libre con el margen indicado")

    orden = count()
    registro = {inicio: (0, None)}
    primera = (prioridad(inicio, 0), next(orden), 0, inicio)
    frontera = deque([primera]) if algoritmo == "BFS" else [primera]
    exploradas = 0
    while frontera:
        if algoritmo == "BFS":
            _, _, costo, actual = frontera.popleft()
        else:
            _, _, costo, actual = heappop(frontera)
        if costo != registro[actual][0]:
            continue
        exploradas += 1
        if actual == meta:
            ruta = [actual]
            while registro[ruta[-1]][1] is not None:
                ruta.append(registro[ruta[-1]][1])
            return {"ruta": ruta[::-1], "costo": costo, "exploradas": exploradas}
        fila, columna = actual
        for vecino in ((fila - 1, columna), (fila, columna + 1),
                       (fila + 1, columna), (fila, columna - 1)):
            if not transitable(vecino):
                continue
            nuevo = costo + 1
            if vecino in registro:
                if algoritmo in ("BFS", "GREEDY") or nuevo >= registro[vecino][0]:
                    continue
            registro[vecino] = (nuevo, actual)
            entrada = (prioridad(vecino, nuevo), next(orden), nuevo, vecino)
            if algoritmo == "BFS":
                frontera.append(entrada)
            else:
                heappush(frontera, entrada)
    return {"ruta": [], "costo": None, "exploradas": exploradas}


def leer_mapa(archivo):
    if archivo.suffix.lower() == ".npy":
        try:
            import numpy
        except ImportError as error:
            raise ValueError("Para NPY usa tu entorno con NumPy o el mapa CSV") from error
        matriz = numpy.load(archivo, allow_pickle=False)
        if matriz.ndim != 2:
            raise ValueError("Se requiere una matriz bidimensional de ocupación")
        datos = matriz.tolist()
    elif archivo.suffix.lower() == ".csv":
        with archivo.open(encoding="utf-8-sig", newline="") as entrada:
            datos = [fila for fila in csv.reader(entrada) if fila]
    else:
        raise ValueError("Selecciona un mapa de ocupación .csv o .npy")
    if not datos or not datos[0] or any(len(fila) != len(datos[0]) for fila in datos):
        raise ValueError("El mapa debe ser una matriz rectangular con datos")
    return [[float(valor) for valor in fila] for fila in datos]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--demo", action="store_true", help="Prueba los cuatro con un mapa incluido")
    modo.add_argument("--mapa", type=Path)
    parser.add_argument("--inspeccionar", action="store_true", help="Muestra los valores del mapa")
    libres = parser.add_mutually_exclusive_group()
    libres.add_argument("--libre", type=float, nargs="+", help="Valores libres exactos")
    libres.add_argument("--libre-max", type=float, help="Valor máximo libre")
    libres.add_argument("--libre-min", type=float, help="Valor mínimo libre")
    parser.add_argument("--inicio", nargs=2, type=int, metavar=("FILA", "COL"))
    parser.add_argument("--meta", nargs=2, type=int, metavar=("FILA", "COL"))
    parser.add_argument("--margen", type=int, default=0, help="Radio de exclusión en celdas")
    parser.add_argument("--algoritmo", type=str.upper, choices=(*ALGORITMOS, "TODOS"), default="TODOS")
    parser.add_argument("--salida", type=Path, help="Guarda resultados en JSON")
    args = parser.parse_args()
    if args.margen < 0:
        parser.error("--margen debe ser como mínimo cero")

    try:
        if args.demo:
            dibujo = [".........", ".###.###.", "...#.....", ".#.#.###.", "........."]
            cuadricula = [[celda == "." for celda in fila] for fila in dibujo]
            inicio, meta = (2, 2), (2, 6)
        else:
            datos = leer_mapa(args.mapa)
            if args.inspeccionar:
                valores = Counter(valor for fila in datos for valor in fila if math.isfinite(valor))
                print(f"Mapa: {len(datos)} filas × {len(datos[0])} columnas")
                if valores:
                    print(f"Rango finito: {min(valores)} a {max(valores)}")
                print(f"Valores más frecuentes (valor, celdas): {valores.most_common(12)}")
                return
            if args.inicio is None or args.meta is None:
                parser.error("Indica --inicio FILA COL y --meta FILA COL")
            if args.libre is not None:
                permitidos = set(args.libre)
                es_libre = permitidos.__contains__
            elif args.libre_max is not None:
                es_libre = lambda valor: valor <= args.libre_max
            elif args.libre_min is not None:
                es_libre = lambda valor: valor >= args.libre_min
            else:
                parser.error("Indica qué celdas son libres con --libre, --libre-max o --libre-min")
            cuadricula = [[math.isfinite(v) and es_libre(v) for v in fila] for fila in datos]
            inicio, meta = tuple(args.inicio), tuple(args.meta)

        algoritmos = ALGORITMOS if args.algoritmo == "TODOS" else (args.algoritmo,)
        resultados = {}
        for algoritmo in algoritmos:
            comienzo = perf_counter()
            resultado = planificar(cuadricula, inicio, meta, algoritmo, args.margen)
            resultado["milisegundos"] = round((perf_counter() - comienzo) * 1000, 3)
            resultados[algoritmo] = resultado
            costo = resultado["costo"] if resultado["ruta"] else "sin ruta"
            print(f"{algoritmo:6} pasos={costo} | exploradas={resultado['exploradas']} "
                  f"| tiempo={resultado['milisegundos']} ms")
        if args.salida:
            args.salida.write_text(
                json.dumps({"inicio": inicio, "meta": meta, "margen": args.margen,
                            "resultados": resultados}, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
