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
            # 1. Sauvegarde sécurisée du PDF d'origine sur le disque
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_in:
                tmp_pdf_in.write(uploaded_file.getvalue())
                tmp_pdf_in_path = tmp_pdf_in.name
                
            # 2. Extraction du XML (le fichier est maintenant bien lisible)
            xml_content = get_xml_from_pdf(tmp_pdf_in_path)
            
            if not xml_content:
                st.error("Aucun fichier XML Factur-X trouvé.")
            else:
                # Gestion du format renvoyé par la bibliothèque
                if isinstance(xml_content, tuple): 
                    xml_content = xml_content[1]
                
                # Conversion en format binaire (bytes) si nécessaire pour éviter l'erreur
                if isinstance(xml_content, str):
                    xml_content = xml_content.encode('utf-8')
                    
                # 3. Modification du XML
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
                    
                    # Sauvegarde du nouveau XML sur le disque
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp_xml:
                        tmp_xml.write(new_xml_content)
                        tmp_xml_path = tmp_xml.name
                        
                    # Préparation du fichier final
                    tmp_pdf_out_path = tempfile.mktemp(suffix=".pdf")
                    
                    # 4. Création du nouveau PDF 
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
                    
                    # Nettoyage
                    os.remove(tmp_xml_path)
                    os.remove(tmp_pdf_out_path)
                else:
                    st.error("Impossible de trouver le bloc ApplicableHeaderTradeAgreement.")
                    
            # Nettoyage du fichier d'origine
            os.remove(tmp_pdf_in_path)

        except Exception as e:
            st.error(f"Une erreur est survenue lors du traitement : {str(e)}")
