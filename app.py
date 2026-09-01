import streamlit as st
import xml.etree.ElementTree as ET
import tempfile
import os
from facturx import get_xml_from_pdf, generate_from_file

st.title("📄 Correcteur Factur-X (Ajout BT-13)")

uploaded_file = st.file_uploader("Glissez la facture PDF ici", type="pdf")
po_reference = st.text_input("Numéro de commande à ajouter (BT-13)")

if uploaded_file and po_reference:
    if st.button("Corriger la facture"):
        try:
            # Création des fichiers temporaires requis par la bibliothèque
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_in, \
                 tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp_xml, \
                 tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_out:
                
                tmp_pdf_in.write(uploaded_file.getvalue())
                tmp_pdf_in_path = tmp_pdf_in.name
                tmp_xml_path = tmp_xml.name
                tmp_pdf_out_path = tmp_pdf_out.name
                
            # 1. Extraction du XML
            xml_content = get_xml_from_pdf(tmp_pdf_in_path)
            
            if not xml_content:
                st.error("Aucun fichier XML Factur-X trouvé.")
            else:
                # Sécurité si la fonction renvoie un tuple (nom_fichier, contenu)
                if isinstance(xml_content, tuple): 
                    xml_content = xml_content[1]
                    
                # 2. Modification du XML
                ET.register_namespace('', "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100")
                root = ET.fromstring(xml_content)
                ns = {'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100'}
                agreement_node = root.find('.//ram:ApplicableHeaderTradeAgreement', ns)
                
                if agreement_node is not None:
                    order_ref = ET.Element("{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BuyerOrderReferencedDocument")
                    issuer_id = ET.SubElement(order_ref, "{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}IssuerAssignedID")
                    issuer_id.text = po_reference
                    agreement_node.append(order_ref)
                    
                    new_xml_content = ET.tostring(root, encoding='utf-8', xml_declaration=True)
                    with open(tmp_xml_path, 'wb') as f:
                        f.write(new_xml_content)
                        
                    # 3. Création du nouveau PDF (re-scellement Factur-X)
                    generate_from_file(tmp_pdf_in_path, tmp_xml_path, output_pdf_file=tmp_pdf_out_path)
                    
                    with open(tmp_pdf_out_path, 'rb') as f:
                        final_pdf_bytes = f.read()
                        
                    st.success("Facture corrigée avec succès !")
                    st.download_button(
                        label="⬇️ Télécharger la nouvelle facture", 
                        data=final_pdf_bytes, 
                        file_name=f"Facture_BT13_{po_reference}.pdf", 
                        mime="application/pdf"
                    )
                else:
                    st.error("Impossible de trouver le bloc ApplicableHeaderTradeAgreement.")
                    
            # Nettoyage automatique des fichiers invisibles
            os.remove(tmp_pdf_in_path)
            os.remove(tmp_xml_path)
            os.remove(tmp_pdf_out_path)

        except Exception as e:
            st.error(f"Une erreur est survenue lors du traitement : {str(e)}")
