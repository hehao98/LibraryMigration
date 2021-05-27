for collection in lioRepository wocDepSeq3 wocRepository lioProject wocCommit libraryGroupArtifact libraryVersion lioProjectDependency lioRepositoryDependency
do
    mongorestore --gzip --archive=/dbdump/migration_helper.$collection.gz
done 