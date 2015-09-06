-- init database

drop database if exists testhome;

create database testhome;

use testhome;

grant select, insert, update, delete on testhome.* to 'www-data'@'localhost' identified by 'www-data';

create table users (
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `password` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_at` real not null,
    unique key `idx_email` (`email`),
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table pageviews (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image ` varchar(500) not null,
    `page_name` varchar(100) not null,
    `element` varchar(100) not null,
    `byway` varchar(50) not null,
    `page_value` varchar(200) not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;


-- email / password:
-- admin@example.com / password

insert into users (`id`, `email`, `password`, `admin`, `name`, `created_at`) values ('0010018336417540987fff4508f43fbaed718e263442526000', 'admin@yoho.com', '5f4dcc3b5aa765d61d8327deb882cf99', 1, 'Administrator', 1402909113.628);