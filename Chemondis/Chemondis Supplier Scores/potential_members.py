from sqlalchemy import create_engine
import pandas as pd
from sqlalchemy import text
import xlsxwriter
user = 'mirror_reader'
pwd = 'Xs5kgnl56ofc60t73K78Hvk9Y'
host = 'mirror-read-replica-rds-chemondis-bi.cxyit1wepgsg.eu-central-1.rds.amazonaws.com'
port = '10101'
db_name = 'mirror'


# establishing Connection
engine = create_engine(f'postgresql://{user}:{pwd}@{host}:{port}/{db_name}')
connection = engine.connect()

query = '''SELECT
    company_mart."name"  AS "company_name",
    company_mart."company_id"  AS "company_id",
    business_owner_mart."name"  AS "Account Owner",
    product_substance_mart."cas_number"  AS "Substance cas_number",
    product_substance_mart."name"  AS "substance_name"
FROM vault.product_mart  AS product_mart
INNER JOIN vault.company_mart  AS company_mart ON (product_mart."company_id_hash_key") = (company_mart."company_id_hash_key")
LEFT JOIN vault.business_owner_mart  AS business_owner_mart ON (company_mart."owner_id_hash_key") = (case when not (business_owner_mart."is_bd_active") then null else business_owner_mart."owner_id_hash_key" end)
LEFT JOIN vault.product_substance_mart  AS product_substance_mart ON (product_substance_mart."product_id_hash_key") = (product_mart."product_id_hash_key")
WHERE (NOT (product_mart."is_supplier_lanxess") OR (product_mart."is_supplier_lanxess") IS NULL) AND (NOT (((company_mart."deleted") is not null) or (((company_mart."name") ~* 'delete')) or ((length((company_mart."name"))) <= 2)) OR (((company_mart."deleted") is not null) or (((company_mart."name") ~* 'delete')) or ((length((company_mart."name"))) <= 2)) IS NULL) AND (NOT (company_mart."is_lanxess") OR (company_mart."is_lanxess") IS NULL) AND (NOT ((DATE(product_substance_mart."deleted" )) is not null ) OR ((DATE(product_substance_mart."deleted" )) is not null ) IS NULL)
GROUP BY
    1,
    2,
    3,
    4,
    5
ORDER BY
    1'''
company_substances = pd.read_sql(text(query), connection)

query2 = '''select z."company_mart.name"                                                 as company,
       z."company_mart.has_active_trial_supplier_membership"                 as in_trial,
       z."company_mart.has_signed_supplier_membership_contract"              as has_signed_up,
       sum(coalesce(z."count_of_product_name", 0))                           as company_top_30_product_count,                             -- number of products that this Supplier has
       sum(coalesce(z."product_mart.total_number_of_requests", 0))           as company_top_30_request_count,                             -- number of requests that this Supplier received
       sum(coalesce(z."negotiation_mart.number_of_requests", 0))             as total_substance_request_count_based_on_company_substances, -- the market addressed by the respective company
       sum(coalesce(z."negotiation_history_mart.total_number_of_offers", 0)) as total_substance_offers_count_based_on_company_substances,  -- total number of offers for this Substance on the marketplace

       round((sum(coalesce(z."product_mart.total_number_of_requests", 0)) /
              sum(coalesce(z."count_of_product_name", 0)))::numeric)         as avg_requests_per_product,                                  -- for the particular Supplier
       case
           when sum(coalesce(z."negotiation_mart.number_of_requests", 0)) = 0 then -1
           else
               round((sum(coalesce(z."product_mart.total_number_of_requests", 0)) /
                      sum(coalesce(z."negotiation_mart.number_of_requests", 0)))::numeric,
                     2) end                                                  as market_share_requests,                                     -- (-1) means that this substance has never been requested on the marketplace

       round((sum(coalesce(z."negotiation_history_mart.total_number_of_offers", 0)) /
              sum(coalesce(z."negotiation_mart.number_of_requests", 1)))::numeric,
             2)                                                              as market_request_to_offer_cr  ,
       -- based on the substances the company lists, what is the conversion rate to offers

       array_agg(z."product_substance_mart.cas_number")                      as cas_list                                                   -- cas numbers of the products that this Supplier has

       -- market share percentag
       -- offer conversion rate for the company in their specific markeet
       --
       -- eventually I''d like to have a blunt percentage which indicates the "probability of success" on our marketplace based on the actual product portfolio
       -- tech wise i imagine this to become just a database view, so we can quickly starting to work with this in looker. No need for a deeper integration into the vault in the first step

from (
         (SELECT company_mart."name"                   AS "company_mart.name",                    -- company name
                 business_owner_mart."name"            AS "business_owner_mart.name",
                 product_substance_mart."cas_number"   AS "product_substance_mart.cas_number",    -- cas number
                 (CASE
                      WHEN company_mart."has_active_supplier_membership" THEN 'Yes'
                      ELSE 'No' END)                   AS "company_mart.has_active_supplier_membership",
                 (CASE
                      WHEN company_mart."has_active_trial_supplier_membership" THEN 'Yes'
                      ELSE 'No' END)                   AS "company_mart.has_active_trial_supplier_membership",
                 (CASE
                      WHEN company_mart."has_signed_supplier_membership_contract" THEN 'Yes'
                      ELSE 'No' END)                   AS "company_mart.has_signed_supplier_membership_contract",
                 COUNT(DISTINCT (product_mart."name")) AS "count_of_product_name",
                 COALESCE(CAST((SUM(DISTINCT
                                    (CAST(FLOOR(COALESCE((product_mart."number_of_requests"), 0) * (1000000 * 1.0)) AS DECIMAL(65, 0))) +
                                    ('x' || MD5(product_mart."product_id_hash_key" ::varchar))::bit(64)::bigint::DECIMAL(65, 0) *
                                    18446744073709551616 +
                                    ('x' || SUBSTR(MD5(product_mart."product_id_hash_key" ::varchar), 17))::bit(64)::bigint::DECIMAL(65, 0)) -
                                SUM(DISTINCT
                                    ('x' || MD5(product_mart."product_id_hash_key" ::varchar))::bit(64)::bigint::DECIMAL(65, 0) *
                                    18446744073709551616 +
                                    ('x' || SUBSTR(MD5(product_mart."product_id_hash_key" ::varchar), 17))::bit(64)::bigint::DECIMAL(65, 0))) AS DOUBLE PRECISION) /
                          CAST((1000000 * 1.0) AS DOUBLE PRECISION),
                          0)                           AS "product_mart.total_number_of_requests" -- number of requests of this product from this particular Supplier
          FROM vault.product_mart AS product_mart
                   INNER JOIN vault.company_mart AS company_mart
                              ON (product_mart."company_id_hash_key") = (company_mart."company_id_hash_key")
                   LEFT JOIN vault.business_owner_mart AS business_owner_mart ON (company_mart."owner_id_hash_key") =
                                                                                 (case
                                                                                      when not (business_owner_mart."is_bd_active")
                                                                                          then null
                                                                                      else business_owner_mart."owner_id_hash_key" end)
                   LEFT JOIN vault.product_substance_mart AS product_substance_mart
                             ON (product_substance_mart."product_id_hash_key") = (product_mart."product_id_hash_key")
          WHERE (NOT (case when (product_mart."deleted") is null then false else true end) OR
                 (case when (product_mart."deleted") is null then false else true end) IS NULL)
            AND (NOT (product_mart."is_lanxess") OR (product_mart."is_lanxess") IS NULL)
            AND (company_mart."number_of_products") >= 1
            AND (product_substance_mart."cas_number") IS NOT NULL
          GROUP BY 1, 2, 3, 4, 5, 6
          ORDER BY 7 DESC) x
             left join
             (SELECT product_substance_mart."cas_number"                          AS "product_substance_mart.cas_number_2",   -- product cas number
                     product_substance_mart."name"                                AS "product_substance_mart.substance_name", -- product substance name
                     COUNT(DISTINCT (negotiation_mart."negotiation_id_hash_key")) AS "negotiation_mart.number_of_requests",   -- how many times this cas_number was requested from all suppliers?
                     COALESCE(CAST((SUM(DISTINCT
                                        (CAST(FLOOR(COALESCE((negotiation_history_mart."number_of_offers"), 0) *
                                                    (1000000 * 1.0)) AS DECIMAL(65, 0))) + ('x' ||
                                                                                            MD5(negotiation_history_mart."negotiation_id_hash_key" ::varchar))::bit(64)::bigint::DECIMAL(65, 0) *
                                                                                           18446744073709551616 +
                                        ('x' ||
                                         SUBSTR(MD5(negotiation_history_mart."negotiation_id_hash_key" ::varchar),
                                                17))::bit(64)::bigint::DECIMAL(65, 0)) - SUM(DISTINCT ('x' ||
                                                                                                       MD5(negotiation_history_mart."negotiation_id_hash_key" ::varchar))::bit(64)::bigint::DECIMAL(65, 0) *
                                                                                                      18446744073709551616 +
                                                                                                      ('x' || SUBSTR(
                                                                                                              MD5(negotiation_history_mart."negotiation_id_hash_key" ::varchar),
                                                                                                              17))::bit(64)::bigint::DECIMAL(65, 0))) AS DOUBLE PRECISION) /
                              CAST((1000000 * 1.0) AS DOUBLE PRECISION),
                              0)                                                  AS "negotiation_history_mart.total_number_of_offers"
              FROM vault.negotiation_mart AS negotiation_mart
                       LEFT JOIN vault.company_mart AS company_mart_supplier
                                 ON (company_mart_supplier."company_id_hash_key") =
                                    (negotiation_mart."seller_id_hash_key")
                       LEFT JOIN vault.product_mart AS product_mart
                                 ON (product_mart."product_id_hash_key") = (negotiation_mart."product_id_hash_key")
                       LEFT JOIN vault.product_substance_mart AS product_substance_mart
                                 ON (product_mart."product_id_hash_key") =
                                    (product_substance_mart."product_id_hash_key")
                       LEFT JOIN vault.negotiation_history_mart AS negotiation_history_mart
                                 ON (negotiation_mart."negotiation_id_hash_key") =
                                    (negotiation_history_mart."negotiation_id_hash_key")
              WHERE (NOT (((company_mart_supplier."deleted") is not null) or
                          (((company_mart_supplier."name") ~* 'delete')) or
                          ((length((company_mart_supplier."name"))) <= 2)) OR
                     (((company_mart_supplier."deleted") is not null) or
                      (((company_mart_supplier."name") ~* 'delete')) or
                      ((length((company_mart_supplier."name"))) <= 2)) IS NULL)
                AND (company_mart_supplier."verified")
                AND (NOT (company_mart_supplier."is_lanxess") OR (company_mart_supplier."is_lanxess") IS NULL)
                AND (product_substance_mart."cas_number") IS NOT NULL
              GROUP BY 1, 2
              HAVING COUNT(DISTINCT (negotiation_mart."negotiation_id_hash_key")) > 0
              ORDER BY 3 DESC
              LIMIT 30) y
         on x."product_substance_mart.cas_number" = y."product_substance_mart.cas_number_2"
         ) z
group by company, in_trial, has_signed_up
order by "total_substance_request_count_based_on_company_substances" desc'''
scores = pd.read_sql(text(query2), connection)

query3 = '''SELECT
    product_substance_mart."name"  AS "substance_name",
    product_substance_mart."cas_number"  AS "Substance cas_number",
    COALESCE(CAST( ( SUM(DISTINCT (CAST(FLOOR(COALESCE( ( product_mart."number_of_requests"  )  ,0)*(1000000*1.0)) AS DECIMAL(65,0))) + ('x' || MD5( product_mart."product_id_hash_key"  ::varchar))::bit(64)::bigint::DECIMAL(65,0)  *18446744073709551616 + ('x' || SUBSTR(MD5( product_mart."product_id_hash_key"  ::varchar),17))::bit(64)::bigint::DECIMAL(65,0) ) - SUM(DISTINCT ('x' || MD5( product_mart."product_id_hash_key"  ::varchar))::bit(64)::bigint::DECIMAL(65,0)  *18446744073709551616 + ('x' || SUBSTR(MD5( product_mart."product_id_hash_key"  ::varchar),17))::bit(64)::bigint::DECIMAL(65,0)) )  AS DOUBLE PRECISION) / CAST((1000000*1.0) AS DOUBLE PRECISION), 0) AS "total_number_of_requests"
FROM vault.product_mart  AS product_mart
INNER JOIN vault.company_mart  AS company_mart ON (product_mart."company_id_hash_key") = (company_mart."company_id_hash_key")
LEFT JOIN vault.product_substance_mart  AS product_substance_mart ON (product_substance_mart."product_id_hash_key") = (product_mart."product_id_hash_key")
WHERE (NOT (case when (product_mart."deleted") is null then false else true end) OR (case when (product_mart."deleted") is null then false else true end) IS NULL) AND ((NOT (product_mart."is_lanxess" ) OR (product_mart."is_lanxess" ) IS NULL) AND (NOT (product_mart."is_supplier_lanxess") OR (product_mart."is_supplier_lanxess") IS NULL)) AND ((product_mart."is_active") AND ((NOT (((company_mart."deleted") is not null) or (((company_mart."name") ~* 'delete')) or ((length((company_mart."name"))) <= 2)) OR (((company_mart."deleted") is not null) or (((company_mart."name") ~* 'delete')) or ((length((company_mart."name"))) <= 2)) IS NULL) AND (product_substance_mart."cas_number" ) IS NOT NULL))
GROUP BY
    1,
    2
ORDER BY
    3 DESC
FETCH NEXT 30 ROWS ONLY'''
top30_data = pd.read_sql(text(query3), connection)

account_owners = '''SELECT
    company_mart."name"  AS "company_name",
    company_mart."company_id"  AS "company_id",
    business_owner_mart."name"  AS "account_owner"
FROM vault.product_mart  AS product_mart
INNER JOIN vault.company_mart  AS company_mart ON (product_mart."company_id_hash_key") = (company_mart."company_id_hash_key")
LEFT JOIN vault.business_owner_mart  AS business_owner_mart ON (company_mart."owner_id_hash_key") = (case when not (business_owner_mart."is_bd_active") then null else business_owner_mart."owner_id_hash_key" end)
GROUP BY
    1,
    2,
    3
ORDER BY
    1'''

account_owners = pd.read_sql(text(account_owners), connection)

top30 = top30_data['substance_name']
top30 = list(top30)

top30_substances_requests = top30_data[['substance_name','total_number_of_requests']]

company_substances['flag'] = company_substances['substance_name'].isin(top30).astype(int)

df = pd.merge(company_substances, top30_substances_requests, on='substance_name',how="left")

df['total_number_of_requests'] = df['total_number_of_requests'].fillna(0)

df_flag = df[['company_id',"company_name",'flag']]
df_reqeust_score = df[['company_id',"company_name",'total_number_of_requests']]
match_count = df_flag.groupby('company_id',as_index=False)['flag'].sum()

request_score = df_reqeust_score.pivot_table(columns=['company_id','company_name'], values='total_number_of_requests', aggfunc='mean').mean().reset_index()

product_density = df_flag.pivot_table(columns=['company_id','company_name'], values='flag', aggfunc='mean').mean().reset_index()

product_density = product_density.rename(columns={0: 'Product Density Score'})
request_score = request_score.rename(columns={0: 'Requests Density Score'})
profile = product_density.merge(request_score,on=['company_id','company_name'])
profile=profile.rename(columns={"company_name": 'company'})
profile["Count of Substances in Top30"] = match_count.flag

merged_scores = scores.merge(profile, on='company', how='left')

merged = merged_scores.merge(account_owners, on='company_id', how='left')
df2 = merged[['company_id','company', 'in_trial', 'has_signed_up', 'account_owner',
       'avg_requests_per_product', 'market_share_requests',
       'market_request_to_offer_cr',
       'Product Density Score', 'Requests Density Score',
       'Count of Substances in Top30']]

# Create an ExcelWriter object and specify the filename
writer = pd.ExcelWriter('Potential Members.xlsx', engine='xlsxwriter')

# Write each dataframe to a separate sheet in the file
df2.to_excel(writer, sheet_name='Scores')
merged.to_excel(writer, sheet_name='All Scores')

# Save the file
writer.save()