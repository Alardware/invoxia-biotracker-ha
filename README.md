# Invoxia GPS & Biotracker pour Home Assistant (non officiel)

Intégration Home Assistant pour les traceurs Invoxia™, pensée d'abord pour le
**Minitailz Biotracker** (collier GPS pour chien), mais compatible avec les
autres traceurs Invoxia (GPS Classic, Mini, Pro, Pet, Bike…).

Pourquoi une nouvelle intégration ? L'intégration
[Invoxia-HA](https://github.com/timothyl13241/Invoxia-HA) s'appuie sur la
bibliothèque `gps-tracker`, qui ne connaît que les anciens types de traceurs
(`tracker_01`, `tracker_03`, `tracker_04`). Dès que le compte contient un
appareil d'un autre type (le Biotracker, par exemple), la bibliothèque lève une
erreur et la configuration s'arrête sur « Unexpected error ». Ici, les réponses
de l'API restent de simples dictionnaires : un type d'appareil, une icône ou une
méthode de localisation inconnus ne font plus planter l'intégration.

## Ce que vous obtenez

Pour chaque traceur du compte :

| Entité | Description |
| --- | --- |
| `device_tracker.<nom>` | Position sur la carte, zones (maison / absent), batterie |
| `sensor.<nom>_batterie` | Batterie (%) |
| `sensor.<nom>_derniere_position` | Date de la dernière position |
| `sensor.<nom>_dernier_signal` | Dernier contact du traceur avec le cloud (diagnostic) |
| `sensor.<nom>_precision_de_la_position` | Précision en mètres (diagnostic) |
| `sensor.<nom>_methode_de_localisation` | gps, wifi, network… (diagnostic) |
| `sensor.<nom>_etat_du_traceur` | État renvoyé par l'API (diagnostic) |

Les noms exacts des entités dépendent du nom du traceur dans l'application
Invoxia (par exemple `device_tracker.rex`).

Les nouveaux traceurs ajoutés au compte apparaissent automatiquement.

**Non disponible :** les données santé du Biotracker (rythme cardiaque,
respiration, activité). Leur API n'est pas documentée ; seule la partie GPS
(identique aux autres traceurs Invoxia) est utilisée.

## Installation

### HACS (recommandé)

[![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Alardware&repository=invoxia-biotracker-ha&category=integration)

1. Supprimez l'ancienne intégration « Invoxia (unofficial) » si vous l'aviez
   ajoutée (Paramètres → Appareils et services), et retirez-la de HACS.
2. Cliquez sur le bouton ci-dessus, ou dans HACS : menu ⋮ → *Dépôts
   personnalisés* → URL `https://github.com/Alardware/invoxia-biotracker-ha`,
   type *Intégration* → *Ajouter*.
3. Ouvrez « Invoxia GPS & Biotracker » dans HACS → *Télécharger*.
4. Redémarrez Home Assistant.

### Manuelle

1. Téléchargez la dernière
   [version](https://github.com/Alardware/invoxia-biotracker-ha/releases).
2. Copiez le dossier `custom_components/invoxia_biotracker` dans le dossier
   `custom_components` de votre configuration Home Assistant (créez-le s'il
   n'existe pas). Vous obtenez `/config/custom_components/invoxia_biotracker/`.
   Pour copier, vous pouvez utiliser les modules complémentaires *Samba share*,
   *Studio Code Server* ou *File editor*.
3. Redémarrez Home Assistant.

## Configuration

1. Paramètres → Appareils et services → **Ajouter une intégration**.
2. Cherchez **Invoxia GPS & Biotracker**.
3. Saisissez l'e-mail et le mot de passe de votre compte Invoxia. Laissez
   l'URL de l'API par défaut (`https://labs.invoxia.io`).

L'intervalle de mise à jour (5 minutes par défaut) se règle dans les options
de l'intégration (bouton *Configurer*), entre 3 et 60 minutes.

## Exemple : alerte si le chien quitte la maison

```yaml
automation:
  - alias: "Le chien a quitté la maison"
    triggers:
      - trigger: zone
        entity_id: device_tracker.rex
        zone: zone.home
        event: leave
    actions:
      - action: notify.notify
        data:
          message: "Le chien vient de quitter la maison !"
```

## En cas de problème

| Message | Signification |
| --- | --- |
| E-mail ou mot de passe incorrect | L'API a répondu 401 : vérifiez vos identifiants dans l'application Invoxia. |
| Impossible de joindre les serveurs Invoxia | Problème réseau ou serveurs Invoxia indisponibles. |
| Aucun traceur | Connexion réussie mais aucun traceur renvoyé. Les journaux listent les types d'appareils reçus. |
| Réponse inattendue | Détails dans les journaux. |

- Journaux : Paramètres → Système → Journaux, cherchez `invoxia_biotracker`.
- Signalez un problème sur
  [GitHub](https://github.com/Alardware/invoxia-biotracker-ha/issues) en
  joignant les diagnostics.
- Diagnostics : Paramètres → Appareils et services → Invoxia GPS & Biotracker
  → ⋮ → **Télécharger les diagnostics**. Le fichier contient les réponses
  brutes de l'API ; mot de passe, e-mail, numéros de série et coordonnées GPS
  y sont masqués.

## Avertissement

Cette intégration utilise l'API privée d'Invoxia™ (la même que l'application
et que la bibliothèque `gps-tracker`). Invoxia ne la documente pas et ne
l'ouvre pas officiellement au public. Gardez un intervalle de mise à jour
raisonnable. Invoxia peut modifier ou fermer cette API à tout moment.

Invoxia™ est une marque d'Invoxia. Ce projet n'est ni affilié à Invoxia ni
approuvé par Invoxia.

## Crédits

- Endpoints et format des réponses : bibliothèque
  [gps_tracker](https://gitlab.com/ezlo.picori/gps_tracker) d'Ezlo Picori
  (licence MIT).
- Idées reprises de [Invoxia-HA](https://github.com/timothyl13241/Invoxia-HA)
  et [gladys-invoxia](https://github.com/LM1LC3N7/gladys-invoxia).

## Développement

```bash
pip install pytest-homeassistant-custom-component
pytest
```

## Licence

MIT — voir [LICENSE](LICENSE).
