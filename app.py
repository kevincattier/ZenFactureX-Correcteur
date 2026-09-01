import streamlit as st
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
            pdf_bytes = uploaded_file.getvalue()
            
            # 1. Extraction du XML
            xml_content = facturx.get_xml_from_pdf(pdf_bytes)
            
            if not xml_content:
                st.error("Aucun fichier XML trouvé dans la facture d'origine.")
            else:
                if isinstance(xml_content, tuple): 
                    xml_content = xml_content[1]
                if isinstance(xml_content, dict):
                    xml_content = list(xml_content.values())[0]
                
                # Conversion en texte brut pour préserver 100% de la structure d'origine
                if isinstance(xml_content, bytes):
                    xml_str = xml_content.decode('utf-8')
                else:
                    xml_str = str(xml_content)
                    
                # 2. Modification du XML par injection directe
                target_tag = "</ram:ApplicableHeaderTradeAgreement>"
                if target_tag not in xml_str:
                    st.error("Balise ApplicableHeaderTradeAgreement introuvable.")
                else:
                    bt13_xml = f"""
    <ram:BuyerOrderReferencedDocument>
        <ram:IssuerAssignedID>{po_reference}</ram:IssuerAssignedID>
    </ram:BuyerOrderReferencedDocument>
</ram:ApplicableHeaderTradeAgreement>"""
                    
                    new_xml_str = xml_str.replace(target_tag, bt13_xml)
                    new_xml_bytes = new_xml_str.encode('utf-8')
                    
                    # 3. Préparation des fichiers temporaires
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_in, \
                         tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_clean, \
                         tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp_xml:
                        
                        tmp_pdf_in.write(pdf_bytes)
                        tmp_xml.write(new_xml_bytes)
                        
                        tmp_pdf_in_path = tmp_pdf_in.name
                        tmp_pdf_clean_path = tmp_pdf_clean.name
                        tmp_xml_path = tmp_xml.name
                        
                    # 4. Suppression de l'ancienne pièce jointe du PDF via Ghostscript
                    os.system(f"gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile={tmp_pdf_clean_path} {tmp_pdf_in_path}")
                    
                    # 5. Incrustation du nouveau XML exclusif
                    tmp_pdf_out_path = tempfile.mktemp(suffix=".pdf")
                    facturx.generate_from_file(tmp_pdf_clean_path, tmp_xml_path, output_pdf_file=tmp_pdf_out_path)
                    
                    with open(tmp_pdf_out_path, 'rb') as f:
                        final_pdf_bytes = f.read()
                        
                    st.success("Facture corrigée avec succès !")
                    st.download_button(
                        label="⬇️ Télécharger la facture finale", 
                        data=final_pdf_bytes, 
                        file_name=f"Facture_BT13_{po_reference}.pdf", 
                        mime="application/pdf"
                    )
                    
                    # Nettoyage sécurisé
                    for p in [tmp_pdf_in_path, tmp_pdf_clean_path, tmp_xml_path, tmp_pdf_out_path]:
                        if os.path.exists(p):
                            os.remove(p)

        except Exception as e:
            st.error("L'application a rencontré une erreur technique.")
            with st.expander("Voir les détails pour le développeur"):
                st.code(traceback.format_exc())
