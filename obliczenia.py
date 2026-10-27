"""Obliczenia przepływów do Etapu 2 (dane: Zestaw_2.csv). Jednostki: kb/s, 1 Mb/s = 1000 kb/s.

Założenia (opisane w rozdz. 3):
- urządzenia bezprzewodowe (WiFi) to dodatkowi użytkownicy, poza 310 komputerami,
- serwery lokalne i internetowe stoją w MDF (Bud. 2, p. 3),
- użytkownik drukuje na drukarkach swojego piętra, ruch rozkłada się równo,
- drukarki są w osobnym VLAN-ie, routing między VLAN-ami w MDF, więc ruch do drukarek
  z budynków obsługiwanych przez IDF przechodzi łączem szkieletowym w obu kierunkach.
"""

G = ["D", "K", "S", "W"]  # Drukarnia, Korektorzy, Konsultanci, WiFi

# użytkownicy na piętrach (W = urządzenia bezprzewodowe)
FLOORS = {
    "B1P1": dict(D=17, K=43, S=39, W=15, printers=1, ap=2),
    "B1P2": dict(D=22, K=17, S=25, W=0, printers=3, ap=0),
    "B2P1": dict(D=5, K=2, S=1, W=12, printers=2, ap=1),
    "B2P2": dict(D=24, K=18, S=35, W=0, printers=2, ap=0),
    "B2P3": dict(D=35, K=5, S=22, W=0, printers=2, ap=0),
}
IDF = {"IDF2": ["B1P1", "B1P2"], "IDF1": ["B2P1", "B2P2"], "MDF": ["B2P3"]}

# (down, up) na użytkownika; down = do użytkownika, up = od użytkownika
S1 = dict(D=(100, 700), K=(200, 250), S=(350, 850), W=(50, 100))
S2 = dict(D=(0, 0), K=(250, 750), S=(0, 0), W=(0, 0))
PR = dict(D=(10, 190), K=(10, 200), S=(10, 120), W=(10, 120))
APPS = {  # Przeglądarka, Wideokonf., VoIP, Klient FTP, Komunikator, Chmura, Poczta
    "D": [(74, 10), (40, 40), (20, 20), (78, 11), (15, 15), (54, 28), (18, 26)],
    "K": [(42, 10), (0, 0), (20, 20), (69, 20), (15, 15), (47, 49), (0, 0)],
    "S": [(61, 10), (40, 40), (0, 0), (0, 0), (15, 15), (0, 0), (10, 29)],
    "W": [(0, 0), (0, 0), (0, 0), (69, 17), (15, 15), (44, 46), (6, 17)],
}
NET = {g: (sum(a[0] for a in APPS[g]), sum(a[1] for a in APPS[g])) for g in G}
# serwery internetowe: (do Internetu, z Internetu, sesje)
WWW, FTP = (130, 25, 33), (130, 50, 3)


def users(floors):
    return {g: sum(FLOORS[f][g] for f in floors) for g in G}


def total(n, table, i):
    return sum(n[g] * table[g][i] for g in G)


ALL = users(FLOORS)


def uplink(floors):
    """(do MDF, z MDF) dla łącza IDF-MDF; ruch drukarek liczony w obu kierunkach."""
    n = users(floors)
    pr = total(n, PR, 0) + total(n, PR, 1)
    to_mdf = total(n, S1, 1) + total(n, S2, 1) + total(n, NET, 1) + pr
    from_mdf = total(n, S1, 0) + total(n, S2, 0) + total(n, NET, 0) + pr
    return to_mdf, from_mdf


def report():
    print("Użytkownicy:", ALL, "razem", sum(ALL.values()))
    print("Internet na użytkownika (down, up):", NET)
    for name, t in [("Serwer1", S1), ("Serwer2", S2), ("Drukarki", PR)]:
        print(f"{name}: do serwera {total(ALL, t, 1)}, od serwera {total(ALL, t, 0)}")
    srv_out = WWW[0] * WWW[2] + FTP[0] * FTP[2]
    srv_in = WWW[1] * WWW[2] + FTP[1] * FTP[2]
    down = total(ALL, NET, 0) + srv_in
    up = total(ALL, NET, 1) + srv_out
    print(f"Internet: użytk. down {total(ALL, NET, 0)} up {total(ALL, NET, 1)}; "
          f"serwery do Int. {srv_out} z Int. {srv_in}")
    print(f"Łącze internetowe: down {down}, up {up}; 40%: {0.4 * down:.1f}, {0.4 * up:.1f}")
    for f, d in FLOORS.items():
        n = {g: d[g] for g in G}
        print(f"{f}: na drukarkę up {total(n, PR, 1) / d['printers']:.1f} "
              f"down {total(n, PR, 0) / d['printers']:.1f}", end="")
        if d["ap"]:
            dn = sum(t["W"][0] for t in (S1, S2, PR, NET)) * d["W"] / d["ap"]
            u = sum(t["W"][1] for t in (S1, S2, PR, NET)) * d["W"] / d["ap"]
            print(f"; na AP down {dn:.1f} up {u:.1f}", end="")
        print()
    for k, fl in IDF.items():
        print(k, "łącze (do MDF, z MDF):", uplink(fl))
    for k, fl in IDF.items():
        devices = sum(sum(FLOORS[f][g] for g in "DKS") + FLOORS[f]["printers"] + FLOORS[f]["ap"]
                      for f in fl)
        print(k, "porty urządzeń:", devices, "z rezerwą 20%:", -(-devices * 12 // 10))
    print("Porty serwerów (S1, S2 po 2 LACP na rdzeniu, WWW i FTP w DMZ): 6, z rezerwą:", -(-6 * 12 // 10))
    print(f"Rdzeń-zapora: do zapory {total(ALL, NET, 1)}, do rdzenia {total(ALL, NET, 0)}")
    # wzrost o 20%: rośnie ruch użytkowników, ruch serwerów internetowych bez zmian
    print(f"Po wzroście o 20%: Internet down {1.2 * total(ALL, NET, 0) + srv_in:.1f} "
          f"up {1.2 * total(ALL, NET, 1) + srv_out:.1f}; 40%: "
          f"{0.4 * (1.2 * total(ALL, NET, 0) + srv_in):.1f} {0.4 * (1.2 * total(ALL, NET, 1) + srv_out):.1f}")
    for k in ("IDF2", "IDF1"):
        print(k, "po wzroście:", tuple(round(1.2 * x, 1) for x in uplink(IDF[k])))
    print("Serwer1 po wzroście:", 1.2 * total(ALL, S1, 1), 1.2 * total(ALL, S1, 0))


if __name__ == "__main__":
    assert sum(ALL.values()) == 337 and ALL == dict(D=103, K=85, S=122, W=27)
    assert NET == dict(D=(299, 150), K=(193, 114), S=(126, 94), W=(134, 95))
    # suma ruchu do rdzenia ze wszystkich pięter = suma wszystkich przepływów od użytkowników
    to_core = sum(uplink(fl)[0] for fl in IDF.values())
    pr_all = total(ALL, PR, 0) + total(ALL, PR, 1)
    assert to_core == total(ALL, S1, 1) + total(ALL, S2, 1) + total(ALL, NET, 1) + pr_all
    report()
