## Drift sur le sentiment FinBERT

Le drift c'est quand la distribution statistique des données change dans le temps par rapport à une référence.
Dans ton cas concret :

Référence (ex: 2021-2023)
→ 40% positive, 35% negative, 25% neutral
→ score moyen : 0.72
→ distribution des scores : centrée sur 0.7

Production (ex: 2025)
→ 20% positive, 60% negative, 20% neutral
→ score moyen : 0.61
→ distribution des scores : décalée vers le bas

Evidently détecte ce décalage statistiquement — il te dit "la distribution de sentiment_score aujourd'hui est significativement différente de ta référence". Ce n'est pas forcément un problème du modèle — c'est peut-être la réalité économique qui a changé. Mais ça mérite d'être signalé

---
## Drift Prophet
Comment Prophet peut dériver

Prophet ne "dérive" pas comme un classifieur — il n'apprend pas en continu. Mais sa qualité de prévision se dégrade quand :

1. Un événement structurel change la tendance
   ex: une crise économique majeure casse le pattern historique
   → la saisonnalité apprise sur 2017-2023 ne tient plus

2. L'intervalle de confiance s'élargit anormalement
   → Prophet est de moins en moins certain de ses projections
   → signal que quelque chose d'inhabituel se passe

3. Le MAE sur les dernières semaines connues augmente
   → les prévisions s'éloignent de la réalité observée

---
## Informations données par le drift

1. Drift FinBERT → distribution de sentiment_score et sentiment_label
   Signal : la réalité économique médiatique a changé
   Action : information, pas forcément réentraînement

2. Qualité Prophet → MAE sur fenêtre glissante récente
   Signal : les prévisions s'éloignent de la réalité
   Action : réentraîner Prophet sur l'historique récent

Il faut pouvoir observer la réalité et une observation de l'incertitude dans la prévisibilité du sentiment est une réalité qu'il faut pouvoir observer donc, sur drift de prophet, retrain et promotion auto