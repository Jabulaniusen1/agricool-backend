-- This query contains farmer specific info per farmer and cooling unit

select uf.id as farmer_id,
       ufcu.coolingunit_id as cooling_unit_id,
       coalesce(max(gender), 'ot')  as gender
from user_farmer uf
left join user_user uu on uu.id = uf.user_id
left join user_farmersurvey ufs on ufs.farmer_id = uf.id
left join user_farmer_cooling_units ufcu on uf.id = ufcu.farmer_id
where ufcu.coolingunit_id is not NULL
group by  uf.id, ufcu.coolingunit_id;
