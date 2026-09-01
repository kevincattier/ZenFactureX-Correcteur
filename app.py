import streamlit as st
import xml.etree.ElementTree as ET
from facturx import extract_xml, generate_facturx
import io

# --- 1. INTERFACE UTILISATEUR ---
st.title("📄 Correcteur Factur-X (Ajout BT-13)")
st.write("Cet outil permet d'ajouter une référence de bon de commande à une facture existante.")

uploaded_file = st.file_uploader("Glissez la facture PDF ici", type="pdf")
po_reference = st.text_input("Numéro de commande à ajouter (BT-13)")

if uploaded_file and po_reference:
    if st.button("Corriger la facture"):
        try:
            # --- 2. EXTRACTION DU XML ---
            pdf_bytes = uploaded_file.read()
            # On extrait le XML incrusté dans le PDF
            _, xml_content = extract_xml(pdf_bytes)
            
            if not xml_content:
                st.error("Aucun fichier XML Factur-X trouvé dans ce PDF.")
            else:
                # --- 3. MODIFICATION DU XML ---
                # On parse le XML
                ET.register_namespace('', "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100")
                root = ET.fromstring(xml_content)
                
                # Définition des espaces de noms
                ns = {'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100'}
                
                # On cherche le noeud ApplicableHeaderTradeAgreement
                agreement_node = root.find('.//ram:ApplicableHeaderTradeAgreement', ns)
                
                if agreement_node is not None:
                    # On crée la nouvelle balise BT-13
                    order_ref = ET.Element("{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BuyerOrderReferencedDocument")
                    issuer_id = ET.SubElement(order_ref, "{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}IssuerAssignedID")
                    issuer_id.text = po_reference
                    
                    # On l'ajoute à l'accord
                    agreement_node.append(order_ref)
                    
                    # On retransforme le XML modifié en texte
                    new_xml_content = ET.tostring(root, encoding='utf-8', xml_declaration=True)
                    
                    # --- 4. CRÉATION DU NOUVEAU PDF ---
                    # On incruste le nouveau XML dans le PDF d'origine
                    new_pdf_stream = io.BytesIO()
                    generate_facturx(new_pdf_stream, pdf_bytes, new_xml_content)
                    new_pdf_stream.seek(0)
                    
                    st.success("Facture corrigée avec succès !")
                    
                    st.download_button(
                        label="⬇️ Télécharger la nouvelle facture",
                        data=new_pdf_stream,
                        file_name=f"Facture_Mise_a_jour_{po_reference}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("Impossible de trouver le bloc ApplicableHeaderTradeAgreement dans le XML.")

        except Exception as e:
            st.error(f"Une erreur est survenue : {str(e)}")
