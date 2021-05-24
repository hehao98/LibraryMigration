for collection in wocDepSeq3 wocRepository wocCommit libraryGroupArtifact libraryVersion lioProject lioProjectDependency lioRepositoryDependency
do
    mongorestore dbdump/ --gzip --archive=migration_helper.$collection.gz
done 