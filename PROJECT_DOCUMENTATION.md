# Documentation technique — AI Chat Lab

Ce document est un support de travail local. Il est volontairement ignoré par Git via `.gitignore` et ne doit pas être commité.

## 1. Vue d’ensemble

AI Chat Lab est une application Django indépendante qui combine :

- une conversation web persistante dans la session Django ;
- un fournisseur Gemini encapsulé dans `ai_engine` ;
- un panneau de tâches persistant en base SQLite ;
- des opérations CRUD manuelles via endpoints JSON ;
- des opérations CRUD proposées par Gemini via Function Calling / Tool Calling.

La règle de sécurité du tool calling est : **l’IA propose, Django valide, Django exécute**. Gemini ne reçoit jamais un accès direct aux modèles Django ou à la base.

## 2. Outils et dépendances

### Dépendances Python

- **Django 5.2** : serveur web, routage, ORM, sessions, CSRF, migrations, tests et administration.
- **google-genai** : SDK officiel utilisé par `GeminiProvider` pour appeler Gemini et déclarer les fonctions disponibles.
- **pydantic 2** : validation stricte des messages et des arguments des outils avant toute opération.
- **python-dotenv** : chargement du fichier `.env` dans `config/settings.py`.
- **httpx** : dépendance utilisée pour reconnaître proprement les erreurs réseau du SDK Gemini.
- **SQLite** : base locale configurée par défaut par Django.

### Dépendances frontend

- **Tailwind CSS via CDN** : classes utilitaires directement dans le template, sans build step.
- **JavaScript vanilla** : `fetch`, manipulation du DOM, gestion des formulaires et rafraîchissement asynchrone.

### Assets statiques

- `static/css/app.css` : styles applicatifs complémentaires, notamment les scrollbar et transitions sobres.
- `static/js/chat.js` : logique frontend du chat, lecture SSE progressive, CRUD des tâches et rafraîchissement du panneau.
- `static/images/.gitkeep` : conserve le dossier prêt à accueillir les images du projet.

### Commandes utiles

- `.venv/bin/python manage.py runserver` : lancer le serveur.
- `.venv/bin/python manage.py migrate` : appliquer les migrations.
- `.venv/bin/python manage.py makemigrations` : générer une migration après modification d’un modèle.
- `.venv/bin/python manage.py test` : exécuter les tests.
- `.venv/bin/python manage.py check` : vérifier la configuration Django.

## 3. Configuration globale

### `config/settings.py`

- `load_dotenv(BASE_DIR / '.env')` charge les secrets locaux.
- `SECRET_KEY`, `DEBUG` et `ALLOWED_HOSTS` sont lus depuis l’environnement.
- `INSTALLED_APPS` contient `chat`, `ai_engine` et `tasks`.
- `GEMINI_API_KEY`, `GEMINI_MODEL` et `GEMINI_TEMPERATURE` configurent Gemini.
- `GEMINI_TIMEOUT_MS`, `GEMINI_MAX_OUTPUT_TOKENS` et `GEMINI_RETRY_ATTEMPTS` limitent respectivement le temps d’attente, la taille de sortie et les tentatives réseau pour éviter les attentes inutiles.
- `CHAT_MAX_MESSAGE_LENGTH` limite un message entrant à 2000 caractères.
- `CHAT_HISTORY_LIMIT` limite l’historique transmis à 20 messages.

### `config/urls.py`

- `/admin/` : administration Django.
- `/` : URLs de l’app `chat`.
- `/api/tasks/` : URLs JSON de l’app `tasks`.

### `config/asgi.py` et `config/wsgi.py`

Points d’entrée standards générés par Django pour les serveurs ASGI et WSGI.

### `manage.py`

Point d’entrée standard des commandes Django.

## 4. App `chat`

Emplacement : `/home/tiayon/Ma_Formation/AI/chat/`.

### Fichiers

- `chat/__init__.py` : marque le dossier comme package Python.
- `chat/admin.py` : enregistre `Conversation` et `Message` dans l’admin.
- `chat/apps.py` : configuration générée de l’app.
- `chat/migrations/__init__.py` : package des migrations.
- `chat/migrations/0001_initial.py` : création des tables de conversation et de message.
- `chat/models.py` : modèles persistants.
- `chat/tests.py` : test de disponibilité de la page.
- `chat/urls.py` : routes HTML et JSON du chat.
- `chat/views.py` : vues de page et d’envoi de message.
- `chat/templates/chat/chat.html` : structure HTML du chat + panneau de tâches ; les styles complémentaires et le JavaScript sont externalisés dans `static/`.

### `chat/models.py`

#### `Conversation`

- `session_key` : identifiant de session Django propriétaire.
- `title` : titre de la conversation.
- `created_at`, `updated_at` : dates de création et de modification.

#### `Message`

- `conversation` : clé étrangère vers `Conversation`.
- `role` : `user` ou `assistant`.
- `content` : contenu du message.
- `created_at` : date de création.

### `chat/views.py`

- `_get_conversation(request)` : crée une session si nécessaire et récupère la conversation correspondante.
- `chat_page(request)` : rend le template avec les messages existants.
- `send_message(request)` : valide le JSON et la longueur, persiste le message utilisateur, transmet l’historique au service IA et renvoie un flux SSE ; la réponse assistant est persistée à la fin du flux.

Le message utilisateur est conservé même si Gemini échoue ; la réponse HTTP reste contrôlée et ne révèle pas de détail sensible.

#### Format du flux SSE

`send_message` renvoie `text/event-stream` avec trois types d’événements JSON :

- `chunk` : morceau de texte reçu de Gemini ;
- `done` : génération terminée et réponse assistant persistée ;
- `error` : erreur contrôlée affichée par le frontend.

Les en-têtes `Cache-Control: no-cache` et `X-Accel-Buffering: no` empêchent autant que possible la mise en tampon par un proxy.

### `chat/urls.py`

- `/` → `chat_page`.
- `/api/messages/` → `send_message`.

## 5. App `tasks`

Emplacement : `/home/tiayon/Ma_Formation/AI/tasks/`.

### Fichiers

- `tasks/__init__.py` : package Python.
- `tasks/admin.py` : configuration d’administration de `Task`.
- `tasks/apps.py` : configuration générée de l’app.
- `tasks/models.py` : modèle `Task`.
- `tasks/services.py` : clonage des données de démonstration et sérialisation JSON.
- `tasks/views.py` : endpoints CRUD JSON.
- `tasks/urls.py` : routes CRUD.
- `tasks/tests.py` : tests CRUD et isolation.
- `tasks/migrations/__init__.py` : package de migrations.
- `tasks/migrations/0001_initial.py` : migration générée par `makemigrations`.
- `tasks/migrations/0002_seed_demo_tasks.py` : migration de données fictives.

### `Task`

Le modèle contient :

- `session_key` (`CharField`) : propriétaire logique de la tâche ; cohérent avec le système de session du chat.
- `title` (`CharField`, 120 caractères) : titre obligatoire.
- `description` (`TextField`) : description facultative.
- `priority` (`CharField`) : `high`, `medium` ou `low`.
- `is_done` (`BooleanField`) : faux par défaut.
- `created_at` (`DateTimeField`) : horodatage automatique.

Le tri affiche d’abord les tâches non terminées, puis les plus récentes.

### `tasks/services.py`

- `ensure_demo_tasks(session_key)` : copie les cinq tâches `TEST — ...` de la session de seed vers une nouvelle session. `task_list` marque ensuite la session avec `demo_tasks_seeded`, ce qui garantit que les tâches de démonstration ne réapparaissent jamais après leur suppression.
- `serialize_task(task)` : transforme un objet ORM en dictionnaire sûr pour le frontend.

### `tasks/views.py`

- `_session_key(request)` : garantit l’existence d’une session Django.
- `_json_body(request)` : décode le corps JSON.
- `task_list` (`GET /api/tasks/`) : initialise les données de démonstration pour la session puis liste uniquement ses tâches.
- `task_create` (`POST /api/tasks/create/`) : valide `title`, `description` et `priority`, puis crée la tâche dans la session.
- `task_update` (`POST /api/tasks/<id>/update/`) : valide les champs modifiables et vérifie la session avant modification.
- `task_delete` (`POST /api/tasks/<id>/delete/`) : supprime uniquement une tâche appartenant à la session courante.

### `tasks/urls.py`

Déclare les quatre routes JSON list/create/update/delete incluses sous `/api/tasks/`.

## 6. App `ai_engine`

Emplacement : `/home/tiayon/Ma_Formation/AI/ai_engine/`.

### Fichiers

- `ai_engine/__init__.py` : package Python.
- `ai_engine/admin.py` : fichier généré, aucune logique admin spécifique.
- `ai_engine/apps.py` : configuration générée.
- `ai_engine/migrations/__init__.py` : package de migrations, sans modèle propre à migrer.
- `ai_engine/models.py` : fichier généré, aucun modèle ; les tâches restent dans `tasks`.
- `ai_engine/views.py` : fichier généré, la logique est appelée par les services.
- `ai_engine/tests.py` : tests du service et des outils.
- `ai_engine/exceptions.py` : exceptions contrôlées.
- `ai_engine/prompts.py` : instruction système de Gemini.
- `ai_engine/schemas.py` : schémas Pydantic.
- `ai_engine/providers.py` : encapsulation du SDK Google.
- `ai_engine/services.py` : orchestration du chat et des tool calls.
- `ai_engine/tools.py` : catalogue, validation et exécution des outils.

### `ai_engine/schemas.py`

- `ChatMessage` : message limité aux rôles `user` et `assistant`.
- `AssistantResponse` : réponse texte non vide.
- `CreateTaskArguments` : arguments contrôlés de création.
- `ListTasksArguments` : argument `only_pending`.
- `UpdateTaskArguments` : id et champs modifiables ; un validateur impose au moins une modification.
- `DeleteTaskArguments` : id positif à supprimer.
- `AnalyzeTasksArguments` : schéma extensible sans argument actuel.
- `ToolCall` : nom d’outil et dictionnaire d’arguments retournés par Gemini.

### `ai_engine/prompts.py`

`DEFAULT_SYSTEM_PROMPT` impose un assistant pédagogique, concis, en français par défaut, qui signale ses incertitudes.

### `ai_engine/providers.py`

#### `GeminiProvider`

- `__init__` : lit la clé et les réglages depuis Django, sans exposer la clé.
- `_generate_content` : encapsule `client.models.generate_content`.
- `generate_reply` : appel texte simple.
- `generate_with_tools` : envoie les déclarations de fonctions à Gemini et extrait les `function_call`.
- `continue_with_tool_results` : renvoie les résultats Django à Gemini pour obtenir le compte-rendu final.
- `_history_contents` : convertit l’historique Django en contenus Gemini.
- `_parse_tool_response` : convertit la réponse SDK en résultat interne.

`ProviderToolResult` transporte le texte, les appels demandés et le contenu modèle nécessaire au second tour. Les erreurs API et réseau deviennent `AIProviderError`.

Le modèle configuré par défaut reste `gemini-2.5-flash`. Si Google le refuse avec une erreur 404 pour une nouvelle clé, le provider utilise automatiquement `gemini-3.6-flash`.

### `ai_engine/tools.py`

- `TOOL_ARGUMENT_SCHEMAS` : associe chaque outil à son modèle Pydantic.
- `TOOL_DESCRIPTIONS` : descriptions envoyées à Gemini.
- `gemini_tool_declarations()` : produit les `FunctionDeclaration` du SDK depuis les schémas Pydantic.
- `_owned_task(task_id, session_key)` : recherche une tâche dans le seul périmètre courant.
- `execute_tool_call(call, session_key)` : valide les arguments, vérifie la propriété, exécute l’ORM et renvoie un résultat court.

Outils disponibles :

- `create_task(title, description, priority)`
- `list_tasks(only_pending)`
- `update_task(task_id, title, description, priority, is_done)`
- `delete_task(task_id)`
- `analyze_tasks()`

`analyze_tasks` calcule ses conseils uniquement sur les tâches dont `session_key` correspond à la session courante.

### `ai_engine/services.py`

`generate_assistant_reply(history, session_key)` :

1. valide l’historique avec Pydantic ;
2. appelle Gemini avec les déclarations d’outils ;
3. si Gemini renvoie un tool call, appelle `execute_tool_call` ;
4. transmet le résultat textuel de Django à Gemini ;
5. répète au maximum trois tours ;
6. renvoie un compte-rendu naturel non vide.

`stream_assistant_reply(history, session_key)` applique le même cycle, mais utilise les générateurs du provider. Chaque morceau de texte est transmis à `chat.views.send_message`, puis au navigateur, sans attendre la fin complète de la génération. Si Gemini demande un outil, Django exécute d’abord l’outil ; le compte-rendu final est ensuite diffusé progressivement.

Le prompt système demande explicitement d’utiliser `analyze_tasks` pour toute demande d’analyse, de rapport, de bilan ou de priorisation. Le résultat de cet outil est construit depuis les tâches de la session courante et est ensuite transformé par Gemini en rapport court et concret.

Pour limiter la latence et le quota consommé, une opération de tâche ne déclenche pas un second appel Gemini de reformulation : après le `function_call`, Django valide et exécute l’outil, puis diffuse directement son résultat textuel court. Une demande d’analyse reçoit donc directement le rapport produit par `analyze_tasks`, et une création reçoit directement la confirmation de création.

Sans `session_key`, le service conserve un mode texte simple utile aux tests et aux usages ne nécessitant pas d’outils.

## 7. Flux de requête — message simple

```text
Navigateur
  │ POST /api/messages/ + message + CSRF
  ▼
chat.views.send_message
  │ valide JSON et limite à 2000 caractères
  │ récupère la session et Conversation
  │ persiste Message(user)
  ▼
ai_engine.services.generate_assistant_reply
  │ valide les 20 derniers messages avec ChatMessage
  ▼
ai_engine.providers.GeminiProvider
  │ appelle Gemini
  ▼
Gemini retourne du texte
  │
chat.views
  │ persiste Message(assistant) à la fin du flux
  ▼
SSE → JavaScript → la bulle assistant s’écrit progressivement
```

## 8. Flux de requête — action CRUD déclenchée par l’IA

```text
Utilisateur : « crée une tâche pour réviser Django »
  ▼
chat.views.send_message
  ▼
GeminiProvider.generate_with_tools
  │ Gemini propose create_task avec des arguments JSON
  ▼
ai_engine.services
  │ reçoit le nom et les arguments
  ▼
ai_engine.tools.execute_tool_call
  │ Pydantic valide title/description/priority
  │ Django filtre Task par session_key
  │ Django crée/modifie/liste/supprime réellement via l’ORM
  │ retourne un résultat court
  ▼
GeminiProvider.continue_with_tool_results
  │ Gemini formule le compte-rendu (« J’ai créé… »)
  ▼
chat.views
  │ persiste la réponse assistant
  ▼
JavaScript
  │ ajoute la réponse au chat
  │ recharge GET /api/tasks/ sans recharger la page
  ▼
Le panneau reflète la base réelle
```

À aucun moment Gemini ne reçoit un objet Django, un queryset ou une connexion à la base.

## 9. Lancement local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# renseigner GEMINI_API_KEY dans .env
python manage.py migrate
python manage.py runserver
```

Ouvrir ensuite http://127.0.0.1:8000/. La première lecture du panneau copie les cinq tâches `TEST — ...` dans la session courante. Cette copie ne se produit qu’une seule fois par session : les suppressions sont définitives. Les tâches créées manuellement sont enregistrées dans la table `tasks_task` avec la session courante comme propriétaire. Les actions du panneau utilisent `fetch` et ne rechargent pas la page.

Tests et contrôles :

```bash
python manage.py check
python manage.py test
```

## 10. Sécurité et limites

- `.env` reste ignoré ; aucune clé Gemini n’est écrite dans le code.
- La clé n’apparaît jamais dans les messages d’erreur.
- Le CSRF Django protège les requêtes POST du frontend.
- Toutes les opérations de tâche sont bornées par `session_key`.
- Les arguments Gemini sont validés avant l’ORM.
- Les messages utilisateur sont limités à 2000 caractères.
- `PROJECT_DOCUMENTATION.md` est ignoré par Git et reste local.

## 11. Interface et assets

Le template principal occupe toute la largeur disponible avec un padding extérieur responsive. La zone de chat est flexible et le panneau des tâches possède une largeur dédiée plus importante sur desktop (`460px`, puis `520px` sur très grands écrans). La palette utilise principalement le blanc et un bleu soutenu.

Sur desktop, le conteneur principal prend la hauteur de la fenêtre et masque le débordement de la page. La zone `#messages` possède `overflow-y-auto` et `min-h-0` : lorsque la conversation devient longue, seul le fil du chat défile. Le panneau de tâches possède lui aussi sa propre zone interne défilante. Sur mobile, la mise en page redevient naturellement verticale.

Pour réduire la latence, le provider utilise le streaming Gemini, une seule tentative réseau par défaut, un timeout de 30 secondes et une sortie limitée à 1024 tokens. Le fichier `.env` local utilise `gemini-3.6-flash`, modèle actuellement disponible pour la clé de développement ; le fallback historique depuis `gemini-2.5-flash` reste présent dans le code. Ces valeurs restent configurables dans `.env`.

Le fichier HTML ne contient plus la logique JavaScript applicative :

- `chat/templates/chat/chat.html` : structure, classes Tailwind et URLs exposées via des attributs `data-*` ;
- `static/js/chat.js` : appels fetch CRUD, lecture du flux SSE avec `ReadableStream`, écriture progressive de la bulle assistant et rafraîchissement des tâches ;
- `static/css/app.css` : styles complémentaires aux classes Tailwind CDN ;
- `static/images/` : emplacement réservé aux images.

Le test `ChatViewTests.test_message_endpoint_streams_and_persists_assistant_reply` vérifie le flux SSE et la persistance de la réponse sans appel réseau réel. Le test `AssistantServiceTests.test_analyze_tool_reports_only_current_session_tasks` vérifie que le rapport ne voit pas les tâches d’une autre session.
