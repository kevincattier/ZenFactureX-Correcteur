import streamlit as st
import xml.etree.ElementTree as ET
from pypdf import PdfReader, PdfWriter
import facturx
import tempfile
import os
import io
import traceback

st.title("📄 Correcteur Factur-X (BT-13 & Nettoyage XML)")

uploaded_file = st.file_uploader("Glissez la facture PDF ici", type="pdf")
po_reference = st.text_input("Numéro de commande à ajouter (BT-13)")

if uploaded_file and po_reference:
    if st.button("Corriger la facture"):
        try:
            pdf_bytes = uploaded_file.getvalue()
            
            # 1. Extraction du XML d'origine
            xml_content = facturx.get_xml_from_pdf(pdf_bytes)
            
            if not xml_content:
                st.error("Aucun fichier XML Factur-X trouvé dans le PDF.")
            else:
                if isinstance(xml_content, tuple):
                    xml_content = xml_content[1]
                if isinstance(xml_content, dict):
                    xml_content = list(xml_content.values())[0]
                if isinstance(xml_content, str):
                    xml_content = xml_content.encode('utf-8')

                # 2. Modification propre du XML avec ElementTree
                namespaces = {
                    'rsm': 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100',
                    'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
                    'udt': 'urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100',
                    'qdt': 'urn:un:unece:uncefact:data:standard:QualifiedDataType:100'
                }
                for prefix, uri in namespaces.items():
                    ET.register_namespace(prefix, uri)

                root = ET.fromstring(xml_content)
                ns = {'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100'}

                # A. Ajout ou mise à jour du BT-13
                agreement = root.find('.//ram:ApplicableHeaderTradeAgreement', ns)
                if agreement is None:
                    st.error("Bloc ApplicableHeaderTradeAgreement introuvable.")
                else:
                    order_ref = agreement.find('ram:BuyerOrderReferencedDocument', ns)
                    if order_ref is None:
                        order_ref = ET.Element('{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BuyerOrderReferencedDocument')
                        agreement.append(order_ref)

                    issuer_id = order_ref.find('ram:IssuerAssignedID', ns)
                    if issuer_id is None:
                        issuer_id = ET.SubElement(order_ref, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}IssuerAssignedID')
                    issuer_id.text = po_reference

                    # B. Suppression de la balise invalide <ram:Description> sous SellerTradeParty
                    seller = agreement.find('ram:SellerTradeParty', ns)
                    if seller is not None:
                        desc = seller.find('ram:Description', ns)
                        if desc is not None:
                            seller.remove(desc)

                    new_xml_bytes = ET.tostring(root, encoding='utf-8', xml_declaration=True)

                    # 3. Nettoyage du PDF (suppression des anciennes pièces jointes)
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    writer = PdfWriter()
                    for page in reader.pages:
                        writer.add_page(page)
                    
                    cleaned_pdf_buf = io.BytesIO()
                    writer.write(cleaned_pdf_buf)
                    cleaned_pdf_bytes = cleaned_pdf_buf.getvalue()

                    # 4. Incrustation du nouveau XML dans le PDF nettoyé
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_in, \
                         tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp_xml:
                        
                        tmp_pdf_in.write(cleaned_pdf_bytes)
                        tmp_xml.write(new_xml_bytes)
                        
                        tmp_pdf_in_path = tmp_pdf_in.name
                        tmp_xml_path = tmp_xml.name

                    tmp_pdf_out_path = tempfile.mktemp(suffix=".pdf")
                    facturx.generate_from_file(tmp_pdf_in_path, tmp_xml_path, output_pdf_file=tmp_pdf_out_path)

                    with open(tmp_pdf_out_path, 'rb') as f:
                        final_pdf_bytes = f.read()

                    # Nettoyage des fichiers temporaires
                    for p in [tmp_pdf_in_path, tmp_xml_path, tmp_pdf_out_path]:
                        if os.path.exists(p):
                            os.remove(p)

                    st.success("✅ BT-13 injecté et erreurs XML corrigées avec succès !")
                    st.download_button(
                        label="⬇️ Télécharger la facture finale",
                        data=final_pdf_bytes,
                        file_name=f"Facture_BT13_{po_reference}.pdf",
                        mime="application/pdf"
                    )

        except Exception as e:
            st.error("L'application a rencontré une erreur technique.")
            with st.expander("Voir les détails pour le développeur"):
                st.code(traceback.format_exc())
