from authentification import (
    formulaire_auth,
    sauvegarder_statut,
    deconnecter_utilisateur,
    creer_client_supabase,
    sauvegarder_session_navigateur,
    charger_progression,
    CLE_SESSION_NAVIGATEUR,
)
from streamlit_local_storage import LocalStorage
import streamlit as st
import json


st.set_page_config(
    page_title="Poly LLG",
    page_icon="assets/logo-louis-le-grand.jpg",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        "About": """# Appli Poly LLG
Cette application n'utilise pas d'exercice originaux et reprend ceux du polycopié LLG.
Elle n'est pas une transcription officielle du poly LLG et peut contenir des erreurs."""
    }
)

local_storage = LocalStorage()


@st.cache_data
def chapitres_exercices():
    with open("data/exercices.json", "r", encoding="utf-8") as file:
        exercices = json.load(file)

    chapitres = {}
    for exercice in exercices["exercices"]:
        chapitre = (exercice["chapitre"]["numero"], exercice["chapitre"]["titre"])
        sous_partie = (exercice["sous_reference"]["numero"], exercice["sous_reference"]["titre"])

        chapitres.setdefault(chapitre, {})
        chapitres[chapitre].setdefault(sous_partie, [])
        chapitres[chapitre][sous_partie].append(exercice)

    return chapitres, exercices["exercices"]


chapitres, exercices = chapitres_exercices()


if "page" not in st.session_state:
    st.session_state.page = "accueil"
if "partie_select" not in st.session_state:
    st.session_state.partie_select = None
if "sous_partie_select" not in st.session_state:
    st.session_state.sous_partie_select = None
if "statuts_exos" not in st.session_state:
    st.session_state.statuts_exos = {}

if "session_navigateur" not in st.session_state:
    session_stockee = local_storage.getItem(CLE_SESSION_NAVIGATEUR)

    if session_stockee is None:
        st.session_state["session_navigateur"] = None
    else:
        st.session_state["session_navigateur"] = session_stockee


STATUTS = ["À faire", "Fait", "À revoir"]

session_stockee = st.session_state.get("session_navigateur")

if not st.session_state.get("utilisateur_id") and session_stockee:
    try:
        if isinstance(session_stockee, str):
            donnees = json.loads(session_stockee)
        else:
            donnees = session_stockee

        client = creer_client_supabase()

        resultat = client.auth.set_session(
            donnees["access_token"],
            donnees["refresh_token"],
        )

        session = resultat.session
        utilisateur = resultat.user

        if session is None or utilisateur is None:
            raise ValueError("La session n'a pas pu être restaurée.")

    except Exception:
        local_storage.setItem(CLE_SESSION_NAVIGATEUR, "")
        st.session_state["session_navigateur"] = None

    else:
        st.session_state.utilisateur_id = utilisateur.id
        st.session_state.email_utilisateur = utilisateur.email
        st.session_state.session_supabase = session.model_dump()
        st.session_state.client_auth = client
        st.session_state.page = "accueil"

        # Sauvegarde les jetons éventuellement renouvelés.
        sauvegarder_session_navigateur(local_storage, session)

        # La progression est indépendante de la restauration de session.
        try:
            st.session_state.statuts_exos = charger_progression(
                client,
                utilisateur.id,
            )
        except Exception:
            st.toast(
                "Connexion restaurée, mais la progression n'a pas pu être chargée."
            )

def changer_partie(chapitre):
    st.session_state.partie_select = chapitre
    st.session_state.sous_partie_select = None
    st.session_state.page = "chapitre"

def changer_sous_partie(chapitre, sous_partie):
    st.session_state.partie_select = chapitre
    st.session_state.sous_partie_select = sous_partie
    st.session_state.page = "sous_partie"

def page_accueil():
    st.session_state.page = "accueil"
    st.session_state.partie_select = None
    st.session_state.sous_partie_select = None

def page_auth():
    st.session_state.page = "auth"
    st.session_state.partie_select = None
    st.session_state.sous_partie_select = None

def page_revisions():
    st.session_state.page = "revisions"
    st.session_state.partie_select = None
    st.session_state.sous_partie_select = None

def statut_exo(exercice):
    return st.session_state.statuts_exos.get(exercice["numero"], "À faire")

def mettre_a_jour_statut(numero):
    statut = st.session_state[f"statut_exo_{numero}"]
    st.session_state.statuts_exos[numero] = statut

    utilisateur_id = st.session_state.get("utilisateur_id")
    client = st.session_state.get("client_auth")

    if utilisateur_id and client:
        try:
            sauvegarder_statut(client, utilisateur_id, numero, statut)
        except Exception:
            st.toast("⚠️ Le statut n'a pas pu être enregistré.")


if st.session_state.page == "auth":
    formulaire_auth(local_storage)
    st.stop()


with st.sidebar:
    col1, col2 = st.columns(2, wrap=False)

    with col1:
        if st.button("🏠 Accueil"):
            page_accueil()
            st.rerun()

    with col2:
        if st.session_state.get("utilisateur_id"):
            if st.button("Déconnexion", type="primary"):
                deconnecter_utilisateur(local_storage)
                page_accueil()
                st.rerun()

        else:
            if st.button("👤 Connexion", type="primary"):
                page_auth()
                st.rerun()

    if any(statut_exo(e) == "À revoir" for e in exercices):
        st.divider()

        if st.button("📖 Exercices à revoir", width="stretch"):
            page_revisions()
            st.rerun()

    st.divider()

    for chapitre, contenu in chapitres.items():
        with st.expander(
            f"{chapitre[0]}. {chapitre[1]}",
            expanded=(chapitre == st.session_state.partie_select)
        ):
            for sous_partie in contenu.keys():
                if st.button(
                    f"{sous_partie[0]} · {sous_partie[1]}",
                    type=(
                        "secondary" if sous_partie == st.session_state.sous_partie_select else "tertiary"
                    ),
                    width="stretch"
                ):
                    changer_sous_partie(chapitre, sous_partie)
                    st.rerun()

if st.session_state.page == "accueil":
    st.title("Poly LLG en ligne")
    st.write("Bienvenue sur la version Web du polycopié LLG/H4.")

    total_exercices = len(exercices)

    nb_faits = sum(
        statut_exo(e) == "Fait" for e in exercices
    )

    col1, col2, col3 = st.columns(3, wrap=False)

    col1.metric("Chapitres", len(chapitres))
    col2.metric("Exercices", total_exercices)
    col3.metric("Faits", nb_faits)

    st.progress(nb_faits / total_exercices)
    st.caption(f"{nb_faits / total_exercices:.0%} des exercices faits")

    st.divider()
    st.subheader("Choisir un chapitre")

    for i in range(0, len(chapitres), 2):
        colonnes = st.columns(2)

        for j, col in enumerate(colonnes):
            index = i + j
            chapitre = list(chapitres.keys())[index]
            sous_parties = chapitres[chapitre]
            exercices_chap = [e for sp in sous_parties.values() for e in sp]
            nb_exercices = len(exercices_chap)
            nb_faits = sum(statut_exo(e) == "Fait" for e in exercices_chap)
            with col:
                with st.container(border=True):
                    st.markdown(f"#### {chapitre[0]}. {chapitre[1]}")
                    st.progress(nb_faits / nb_exercices)
                    st.markdown(f"**{len(sous_parties)} parties** · **{nb_exercices} exercices**")

                    if st.button("Ouvrir le chapitre →", key=f"ouvrir_chapitre_{chapitre[0]}"):
                        changer_partie(chapitre)
                        st.rerun()

    st.subheader("Statistiques par difficulté")
    cols = st.columns(5)
    for i, col in enumerate(cols):
        exos_par_diff = [e for e in exercices if e["difficulte"] == i + 1]
        nb_exos = len(exos_par_diff)
        nb_faits = sum(
            statut_exo(e) == "Fait" for e in exos_par_diff
        )

        with col:
            st.markdown(f"#### Exercices {"★" * (i + 1)}")
            st.progress(nb_faits / nb_exos)
            st.caption(f"{nb_faits} / {nb_exos} terminés")

    st.divider()
    st.info(
        "Ce site n'est pas une transcription officielle du polycopié LLG. "
        "Certains exercices et corrigés peuvent être mal transcris ou contenir des erreurs. "
        "Vous êtes invités à vous référer au document original.",
        icon="⚠️"
    )

elif st.session_state.page == "revisions":
    revisions_exos = [
        e for e in exercices if statut_exo(e) == "À revoir"
    ]
    nb_revisions = len(revisions_exos)

    st.header(
        f"{nb_revisions} exercice{"s" if nb_revisions > 1 else ""} à revoir"
    )

    for exo in revisions_exos:
        with st.container(border=True, width="stretch"):
            col_titre, col_statut = st.columns([4, 1])
            with col_titre:
                st.markdown(f"#### Exercice {exo["numero"]} ({"★" * exo["difficulte"]})")
                st.write(f"De **{exo["sous_reference"]["numero"]} : {exo["sous_reference"]["titre"]}**")
                if exo["titre"] is not None:
                    st.caption(
                        f"**{exo["titre"]}{" (∗)" if exo["is_classique"] else ""}**"
                    )
            with col_statut:
                statut = st.radio(
                    "Statut",
                    STATUTS,
                    index=STATUTS.index(statut_exo(exo)),
                    key=f"statut_exo_{exo["numero"]}",
                    on_change=mettre_a_jour_statut,
                    args=(exo["numero"],),
                    label_visibility="collapsed",
                )
            st.markdown(exo["enonce_md"])
            with st.expander("Corrigé", expanded=False):
                st.markdown(exo["corrige_md"])
                st.caption(f"Par {exo["auteur_corrige"]}")

elif st.session_state.page == "chapitre":
    chapitre = st.session_state.partie_select

    st.title(f"{chapitre[0]}. {chapitre[1]}")

    for sous_partie, exos in chapitres[chapitre].items():
        nb_faits = sum(
            statut_exo(e) == "Fait" for e in exos
        )

        with st.container(border=True):
            st.markdown(f"#### {sous_partie[0]} · {sous_partie[1]}")
            st.progress(nb_faits / len(exos))
            st.caption(f"{nb_faits}/{len(exos)} exercices terminés")
            if st.button("Ouvrir la partie →", key=f"ouvrir_sous_partie_{sous_partie[0]}"):
                changer_sous_partie(chapitre, sous_partie)
                st.rerun()

elif st.session_state.page == "sous_partie":
    chapitre = st.session_state.partie_select
    sous_partie = st.session_state.sous_partie_select

    col1, col2 = st.columns([4, 1])

    with col1:
        st.caption(f"{chapitre[0]}. {chapitre[1]} / {sous_partie[0]} · {sous_partie[1]}")
        st.title(sous_partie[1])
    with col2:
        afficher_corriges = st.toggle(
            "Afficher les corrigés", value=True, key=f"corriges_{sous_partie[0]}"
        )

    exercices_sp = chapitres[chapitre][sous_partie]

    for exercice in exercices_sp:
        with st.container(border=True, width="stretch"):
            url_enonce = (
                "https://www.louislegrand.fr/wp-content/uploads/2022/01/EXOS-TERMINALE3-3-AVECDESSIN.pdf"
                f"#page={exercice["source"]["poly_page"]}"
            )
            url_corrige = (
                "https://wikiprepa.fr/wp-content/uploads/Correction_Poly_Transition_Prepa_LLG_H4.pdf"
                f"#page={exercice["source"]["corrige_pages"][0]}"
            )

            col_titre, col_statut = st.columns([4, 1])
            with col_titre:
                st.markdown(f"#### Exercice {exercice["numero"]} ({"★" * exercice["difficulte"]})")
                if exercice["titre"] is not None:
                    st.caption(
                        f"**{exercice["titre"]}{" (∗)" if exercice["is_classique"] else ""}** - [Source]({url_enonce})"
                    )
                else:
                    st.caption(f"[Source]({url_enonce})")
            with col_statut:
                statut = st.radio(
                    "Statut",
                    STATUTS,
                    index=STATUTS.index(statut_exo(exercice)),
                    key=f"statut_exo_{exercice["numero"]}",
                    on_change=mettre_a_jour_statut,
                    args=(exercice["numero"],),
                    label_visibility="collapsed",
                )

            st.markdown(exercice["enonce_md"])

            if afficher_corriges:
                with st.expander("Corrigé", expanded=False):
                    st.markdown(exercice["corrige_md"])
                    st.caption(f"Par {exercice["auteur_corrige"]} - [Source]({url_corrige})")

    st.divider()

    toutes_sous_parties = [
        (chap, sp) for chap, sous_parties in chapitres.items()
        for sp in sous_parties.keys()
    ]
    index_actuel = toutes_sous_parties.index(
        (chapitre, sous_partie)
    )

    col1, col2 = st.columns(2, wrap=False)
    with col1:
        if index_actuel > 0:
            chap_precedent, sp_precedente = toutes_sous_parties[index_actuel - 1]
            if st.button("← Sous-partie précédente"):
                changer_sous_partie(chap_precedent, sp_precedente)
                st.rerun()
    with col2:
        if index_actuel < len(toutes_sous_parties) - 1:
            chap_suivant, sp_suivante = toutes_sous_parties[index_actuel + 1]
            with st.container(horizontal_alignment="right"):
                if st.button("Sous-partie suivante →"):
                    changer_sous_partie(chap_suivant, sp_suivante)
                    st.rerun()
