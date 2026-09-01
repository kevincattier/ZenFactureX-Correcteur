import streamlit as st
import xml.etree.ElementTree as ET
import tempfile
import os
import traceback
import facturx

st.title("📄 Correcteur Factur-X (Ajout BT-13)")

uploaded_file = st.file_uploader("Glissez la facture PDF ici", type="pdf")
po_reference = st.text_input("Numéro de commande à ajouter (BT-13)")

if uploaded_file and po_reference:
    if st.button("Corriger la facture"):
        try:
            # Récupération des octets bruts du PDF
            pdf_bytes = uploaded_file.getvalue()
            
            # 1. Extraction du XML (directement depuis les octets en mémoire)
            xml_content = facturx.get_xml_from_pdf(pdf_bytes)
            
            if not xml_content:
                st.error("Aucun fichier XML Factur-X trouvé.")
            else:
                if isinstance(xml_content, tuple): 
                    xml_content = xml_content[1]
                if isinstance(xml_content, dict):
                    xml_content = list(xml_content.values())[0]
                if isinstance(xml_content, str):
                    xml_content = xml_content.encode('utf-8')
                    
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
                    
                    # 3. Création des fichiers physiques pour l'incrustation PDF/A-3
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_in, \
                         tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp_xml:
                        tmp_pdf_in.write(pdf_bytes)
                        tmp_xml.write(new_xml_content)
                        tmp_pdf_in_path = tmp_pdf_in.name
                        tmp_xml_path = tmp_xml.name
                        
                    tmp_pdf_out_path = tempfile.mktemp(suffix=".pdf")
                    
                    # 4. Génération finale
                    facturx.generate_from_file(tmp_pdf_in_path, tmp_xml_path, output_pdf_file=tmp_pdf_out_path)
                    
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
                    os.remove(tmp_pdf_in_path)
                    os.remove(tmp_xml_path)
                    if os.path.exists(tmp_pdf_out_path):
                        os.remove(tmp_pdf_out_path)
                else:
                    st.error("Impossible de trouver le bloc ApplicableHeaderTradeAgreement.")

        except Exception as e:
            st.error("L'application a rencontré une erreur technique.")
            with st.expander("Voir les détails pour le développeur"):
                st.code(traceback.format_exc())
