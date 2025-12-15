## Conventions de nommage

# Convention de nommage des tickets
Tous les tickets sont nommés en suivant le pattern patterne `<SOURCE><numéro> - <titre>`

    Exemples:
CYBER3 - creation HDFS
DEV14 - gateway frontend
DATA29 - heatmap collection des poubelles

# Convention de nommage des branches
Toutes les branches suivent la forme suivante : `<type>/<ticket>-<description>`
    
    Types:
`feature` -> nouvelle fonctionnalité
`fix` -> correctif d'une fonctionalité existante
`update` -> amélioration d'un fonctionnalité (refacto ou ajout)

    Tickets:
L'identifiant Trello du ticket traité, afin de rassembler facilement les éléments liés

    Description:
La description ce fait par mots clés permettant d'avoir une idée générale du contenu de la branche

    Exemples:
`feature/22-creation-bdd`
`fix/43-modele-predictif`
`update/22-ajout-parametre-heatmap`

# Conventions de nommage des dossiers
Tous les dossiers sont nommés explicitement en snake case (mon_nouveau_dossier)

# Convention de nommage des fichiers
Tous les fichiers sont nommés explicitement en snake case (mon_nouveau_fichier.py)

# Convention de nommage des fonctions
Toutes les fonctions sont nommées en sake case (def ma_fonction():) explicite et possède une docstring associée afin d'expliquer clairement le traitement effecuté, les différents paramètres d'entrés (avec leur type) ainsi que la valeur retournée (avec son type)

    Exemple:
def affiche_message(message: str): -> None
    """
    Affiche un message dans la console de l'utilisateur. Prend en paramètre d'entrée un string contenant le message à afficher et ne renvoie rien.
    """
    print(message)

# Convention de nommage des variables
Toutes les variables sont nommées de manière explicite en snake case (parametres_utilisateur). Les variables itérées (for var) doivent ne faire qu'un seul mot, qui est un diminutif du contenu sur lequel elle itère.

    Exemple:
panier_fruits = ['poire', 'banane', 'pomme']
for fruit in panier_fruits:
    print(fruit)

--------------------------------------------------------------------------------

## Pratiques Git

# Rapport à la branche main
La branche main est notre branche de 'production', elle ne contient donc que le code qui a été validé via les pull request.

# Commit message
Chaque commit doit avoir un court message résumant le contenu du commit.

    Exemple:
git commit -m "Add a processes file to normalize workflow"

# Pull Requests
Quand une branche feature/fix/update est prête à être déployée (but atteint et branche à jour), une pull request doit être faite afin de la fusionner sur la branche main. Le code quoi être revu et approuvé par au moins deux personnes autres que le responsable de la branche.

Toutes les branches doivent être SQUASH MERGE afin de conserver l'historique de main linéaire et épuré.

Une fois la branche déployée, elle doit être supprimée.

--------------------------------------------------------------------------------

## Pratiques Trello

# Cycle de vie du ticket
Les tickets sont répartis par état : backlog, rafinement, à faire, en cours, bloqué, revue, terminé

Backlog    -> état initial du ticket, c'est là que chaque nouveau ticket doit apparaître
Rafinement -> état de planification du ticket, c'est par là qu'un ticket doit passer avant d'être affecté afin de déterminer comment le traiter
A Faire    -> état de pré-traitement du ticket, il est affecté à un membre de l'équipe qui devra le traîter
En Cours   -> était de traitement du ticket, le membre de l'équipe traîte activement le ticket attribué
Bloqué     -> état que prend le ticket lorsque son traitement est interrompu, et ne peut reprendre tant qu'une autre tache n'est pas faite
Revue      -> état que prend le ticket lorsque que son traitement est terminé, et n'a plus qu'a être validé pour être colturé
Terminé    -> état que prend le ticket lorsque que son traitement est terminé et validé

