Documentation on the Database general structure :

Each file is named as such : SQL_"Table_name"

SQL_Container is the table used for the intelligent container and their position (organized via B-Tree Index)

SQL_Measurements is the table used for the measurement sent by the containers (organized via BRIN Index)

SQL_Role is the table that contains the 4 different roles archetypes used by the RLS (Admin, Manager, Workers, User)

SQL_Signalements is the table that contains users reports based on observations of identified containers

SQL_Teams is the table that contains the different teams of workers linked to the various patrols

SQL_Tournees is the table that contains the different patrols made to supposedly keep containers for overflowing, each of them is supposed to be updated daily.

SQL_Urban_Zones is the table that contains the different cities that are covered by the system and handled by the data teams

SQL_User_Role is a junction table between Users and Role
SQL_User_Team is a junction table between Users and Team

SQL_Users_History is the logging table for the user table, it is handled using a GIN index.

SQL_USERS is the table that contains all users including password etcetera.
