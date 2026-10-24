import streamlit as st
from supabase import create_client
import json


CLE_SESSION_NAVIGATEUR = "poly_llg_session"


def creer_client_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


def charger_progression(client, utilisateur_id):
    resultat = (
        client.table("progression")
        .select("exercice_id, statut")
        .eq("user_id", utilisateur_id)
        .execute()
    )

    return {
        int(ligne["exercice_id"]): ligne["statut"]
        for ligne in resultat.data
    }


def sauvegarder_statut(client, utilisateur_id, exercice_id, statut):
    (
        client.table("progression")
        .upsert(
            {
                "user_id": utilisateur_id,
                "exercice_id": str(exercice_id),
                "statut": statut,
            },
            on_conflict="user_id,exercice_id",
        )
        .execute()
    )


def deconnecter_utilisateur(local_storage):
    client = st.session_state.get("client_auth")

    if client is not None:
        try:
            client.auth.sign_out()
        except Exception:
            st.warning("La déconnexion auprès de Supabase a échoué.")

    try:
        local_storage.setItem(CLE_SESSION_NAVIGATEUR, "")
    except Exception:
        st.warning(
            "La session enregistrée dans le navigateur "
            "n'a pas pu être effacée."
        )

    for cle in (
        "utilisateur_id",
        "email_utilisateur",
        "session_supabase",
        "client_auth",
    ):
        st.session_state.pop(cle, None)

    st.session_state.statuts_exos = {}


def sauvegarder_session_navigateur(local_storage, session):
    donnees = {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
    }

    local_storage.setItem(
        CLE_SESSION_NAVIGATEUR,
        json.dumps(donnees),
    )


def formulaire_auth(local_storage):
    client = creer_client_supabase()

    onglet_connexion, onglet_inscription = st.tabs(
        ["Connexion", "Créer un compte"]
    )

    with onglet_connexion:
        with st.form("connexion"):
            email = st.text_input("Adresse e-mail", type="email")
            mot_passe = st.text_input("Mot de passe", type="password")

            envoyer = st.form_submit_button("Se connecter")

        if envoyer:
            try:
                resultat = client.auth.sign_in_with_password({
                    "email": email,
                    "password": mot_passe
                })

                st.session_state.utilisateur_id = resultat.user.id
                st.session_state.email_utilisateur = resultat.user.email

                st.session_state.session_supabase = resultat.session.model_dump()

                sauvegarder_session_navigateur(
                    local_storage,
                    resultat.session,
                )

                st.session_state.page = "accueil"
                st.session_state.client_auth = client
                st.success("Connexion réussie !")

                st.session_state.statuts_exos = charger_progression(
                    client, resultat.user.id
                )

                st.rerun()

            except Exception as e:
                st.error("Connexion impossible. Vérifiez vos identifiants.")

    with onglet_inscription:
        with st.form("inscription"):
            email_inscription = st.text_input("Adresse e-mail", type="email")
            mot_passe_inscription = st.text_input("Mot de passe", type="password")
            confirmation = st.text_input("Confirmation", type="password")

            envoyer_inscription = st.form_submit_button("Créer mon compte")

        if envoyer_inscription:
            if mot_passe_inscription != confirmation:
                st.error("Les deux mots de passe ne correspondent pas")

            elif len(mot_passe_inscription) < 10:
                st.error("Le mot de passe doit comporter au moins 10 caractères")

            else:
                try:
                    resultat = client.auth.sign_up({
                        "email": email_inscription,
                        "password": mot_passe_inscription
                    })

                    if resultat.session is None:
                        st.success("Compte créé ! Vérifiez vos e-mails pour confirmer votre compte.")
                    else:
                        st.session_state.utilisateur_id = resultat.user.id
                        st.session_state.email_utilisateur = resultat.user.email
                        st.session_state.session_supabase = resultat.session.model_dump()

                        sauvegarder_session_navigateur(
                            local_storage,
                            resultat.session,
                        )

                        st.session_state.page = "accueil"
                        st.session_state.client_auth = client
                        st.success("Compte créé et connexion réussie !")

                        st.session_state.statuts_exos = charger_progression(
                            client, resultat.user.id
                        )

                        st.rerun()
                except Exception:
                    st.error("Impossible de créer le compte.")

    return None
