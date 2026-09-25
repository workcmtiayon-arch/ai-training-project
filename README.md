# AI Chat Lab

AI Chat Lab est un projet Django d’apprentissage pratique : il propose une interface de chat web sobre, persistante par session Django, et connectée à l’API Gemini de Google.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

Copiez `.env.example` vers `.env` et renseignez `GEMINI_API_KEY`. Une clé peut être créée depuis [Google AI Studio](https://aistudio.google.com/apikey). La clé Django de développement est générée automatiquement par le script d’initialisation, ou peut être remplacée dans `.env`.

## Lancement

```bash
python manage.py migrate
python manage.py runserver
```

Ouvrez ensuite http://127.0.0.1:8000/. Chaque navigateur possède sa conversation via sa session Django. L’API reçoit les 20 derniers messages et limite chaque message entrant à 2000 caractères.

## Comptes et authentification

Les comptes sont gérés par le système d’authentification natif de Django et sont enregistrés dans la base de données (`auth_user`).

- Inscription : http://127.0.0.1:8000/comptes/inscription/
- Connexion : http://127.0.0.1:8000/comptes/connexion/
- Déconnexion : le bouton présent dans l’application

Les mots de passe sont hachés par Django. Le chat et l’API des tâches nécessitent une session utilisateur authentifiée.

Pour vérifier le projet :

```bash
python manage.py test
python manage.py check
```

## Structure

- `config/` : réglages Django, URLs et configuration chargée depuis `.env`.
- `chat/` : modèles `Conversation` et `Message`, vues HTTP/JSON, URLs et template Tailwind/JavaScript.
- `ai_engine/` : séparation `service → provider → schémas`, prompt système et exceptions dédiées. Le provider utilise `gemini-2.5-flash` par défaut.
- `requirements.txt` : dépendances Python.
- `.env.example` : modèle committable ; `.env` reste ignoré par Git.

Le code ne contient aucune clé API. En production, désactivez le debug, définissez des hôtes autorisés stricts et utilisez un secret Django conservé dans le gestionnaire de secrets de votre environnement.
