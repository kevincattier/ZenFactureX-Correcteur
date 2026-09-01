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
            # Lecture du fichier envoyé
            pdf_bytes = uploaded_file.getvalue()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_in:
                tmp_pdf_in.write(pdf_bytes)
                tmp_pdf_in_path = tmp_pdf_in.name
                
            # Extraction du XML
            xml_content = facturx.get_xml_from_pdf(tmp_pdf_in_path)
            
            if not xml_content:
                st.error("Aucun fichier XML Factur-X trouvé.")
            else:
                # Sécurisation stricte des formats de retour (tuple, dict, str)
                if isinstance(xml_content, tuple): 
                    xml_content = xml_content[1]
                if isinstance(xml_content, dict):
                    # Récupération de la première pièce jointe du dictionnaire
                    xml_content = list(xml_content.values())[0]
                if isinstance(xml_content, str):
                    xml_content = xml_content.encode('utf-8')
                    
                # Modification du XML (format binaire garanti)
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
                    
                    # Génération du nouveau PDF
                    final_pdf_bytes = None
                    
                    # On privilégie la méthode en mémoire si disponible
                    if hasattr(facturx, 'generate_facturx'):
                        final_pdf_bytes = facturx.generate_facturx(pdf_bytes, new_xml_content)
                    else:
                        # Sinon, méthode par fichiers physiques
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp_xml:
                            tmp_xml.write(new_xml_content)
                            tmp_xml_path = tmp_xml.name
                            
                        tmp_pdf_out_path = tempfile.mktemp(suffix=".pdf")
                        facturx.generate_from_file(tmp_pdf_in_path, tmp_xml_path, output_pdf_file=tmp_pdf_out_path)
                        
                        with open(tmp_pdf_out_path, 'rb') as f:
                            final_pdf_bytes = f.read()
                            
                        os.remove(tmp_xml_path)
                        if os.path.exists(tmp_pdf_out_path):
                            os.remove(tmp_pdf_out_path)
                            
                    st.success("Facture corrigée avec succès !")
                    st.download_button(
                        label="⬇️ Télécharger la nouvelle facture", 
                        data=final_pdf_bytes, 
                        file_name=f"Facture_BT13_{po_reference}.pdf", 
                        mime="application/pdf"
                    )
                else:
                    st.error("Impossible de trouver le bloc ApplicableHeaderTradeAgreement.")
                    
            # Nettoyage
            if os.path.exists(tmp_pdf_in_path):
                os.remove(tmp_pdf_in_path)

        except Exception as e:
            st.error("L'application a rencontré une erreur technique.")
            with st.expander("Voir les détails pour le développeur"):
                st.code(traceback.format_exc())
